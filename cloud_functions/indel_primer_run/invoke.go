package main

// VERSION v2

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path"
	"time"

	"cloud.google.com/go/datastore"
	"cloud.google.com/go/storage"
)

const indelPrimerVersion = "v2"
const datasetName = "input.json"
const resultName = "results.tsv"
const bucketName = "elegansvariation.org"
const projectID = "andersen-lab"

type Payload struct {
	Site    string
	Hash    string
	Strain1 string
	Strain2 string
	Vcf_url string
	Ds_id   string
	Ds_kind string
}

type dsInfo struct {
	Kind      string
	Id        string
	Msg       string
	Data_hash string
}

type dsEntry struct {
	Username    string         `datastore:"username"`
	Data_hash   string         `datastore:"data_hash"`
	Site        string         `datastore:"site"`
	Strain1     string         `datastore:"strain1"`
	Strain2     string         `datastore:"strain2"`
	Empty       bool           `datastore:"empty"`
	Status      string         `datastore:"status"`
	Status_msg  string         `datastore:"status_msg,noindex"`
	Modified_on time.Time      `datastore:"modified_on"`
	Created_on  time.Time      `datastore:"created_on"`
	K           *datastore.Key `datastore:"__key__"`
}

func check(e error, i dsInfo) {
	if e != nil {
		msg := e.Error() + "\n" + i.Msg
		setDatastoreStatus(i.Kind, i.Id, "ERROR", msg)
		panic(e)
	}
}

func setDatastoreStatus(kind string, id string, status string, msg string) {
	ctx := context.Background()
	dsClient, err := datastore.NewClient(ctx, projectID)
	if err != nil {
		log.Fatal(err)
	}
	defer dsClient.Close()

	k := datastore.NameKey(kind, id, nil)
	e := new(dsEntry)
	if err := dsClient.Get(ctx, k, e); err != nil {
		log.Fatal(err)
	}

	e.Status = status
	e.Status_msg = msg

	if _, err := dsClient.Put(ctx, k, e); err != nil {
		log.Fatal(err)
	}

	fmt.Printf("Updated status: %q\n", e.Status)
	fmt.Printf("Updated status msg: %q\n", e.Status_msg)

}

func downloadFile(filepath string, url string) error {

	// Get the data
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	// Create the file
	out, err := os.Create(filepath)
	if err != nil {
		return err
	}
	defer out.Close()

	// Write the body to file
	_, err = io.Copy(out, resp.Body)
	return err
}

func copyBlob(bucket string, source string, blob string, i dsInfo) {
	log.Printf("%s --> %s", source, blob)
	ctx := context.Background()
	client, err := storage.NewClient(ctx)
	check(err, i)

	// source
	f, err := os.Open(source)
	if err != nil {
		log.Fatal(err)
	}
	defer f.Close()

	wc := client.Bucket(bucket).Object(blob).NewWriter(ctx)
	_, err = io.Copy(wc, f)
	check(err, i)
	err = wc.Close()
	check(err, i)
}

func fileExists(filename string) bool {
	info, err := os.Stat(filename)
	if os.IsNotExist(err) {
		return false
	}
	return !info.IsDir()
}

func runIndelPrimer(p Payload, i dsInfo) ([]byte, error) {
	/*
		Runs the herritability analysis
	*/

	// Run the heritability analysis. This is used to run it in the background.
	// Execute R script

	site := p.Site
	dataHash := p.Hash
	strain1 := p.Strain1
	strain2 := p.Strain2
	vcfURL := p.Vcf_url

	// Download Index
	indexURL := fmt.Sprintf("%s.csi", vcfURL)
	downloadFile(path.Base(indexURL), indexURL)

	log.Printf("vk primer indel --region %v --nprimers 10 --ref=WS276 --samples=%v %v", site, fmt.Sprintf("%s,%s", strain1, strain2), vcfURL)
	cmd := exec.Command("conda",
		"run",
		"-n",
		"vcf-kit",
		"vk",
		"primer",
		"indel",
		"--region",
		site,
		"--nprimers",
		"10",
		"--polymorphic",
		"--ref",
		"WS276",
		"--samples",
		fmt.Sprintf("%s,%s", strain1, strain2),
		vcfURL)

	cmd.Stderr = os.Stderr
	out, err := cmd.Output()
	fmt.Println(out)
	check(err, i)
	fmt.Println(err)

	// write file to output
	ioutil.WriteFile(resultName, out, 0755)

	resultBlob := fmt.Sprintf("reports/indel_primer/%s/%s", dataHash, resultName)
	copyBlob(bucketName, resultName, resultBlob, i)

	return out, err

}

func ipHandler(w http.ResponseWriter, r *http.Request) {
	/*
		Handler for google cloud task which triggers a heritability calculation
	*/
	// Check header to verify the request is from a Cloud Task
	taskName := r.Header.Get("X-Cloudtasks-Taskname")
	if taskName == "" {
		log.Println("Invalid Task: No X-Appengine-Taskname request header found")
		http.Error(w, "Bad Request - Invalid Task", http.StatusBadRequest)
		return
	}

	// Pull useful headers from Task request.
	queueName := r.Header.Get("X-Cloudtasks-Queuename")

	// Extract the request body for further task details.
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		log.Printf("ReadAll: %v", err)
		http.Error(w, "Internal Error", http.StatusInternalServerError)
		return
	}

	// Log & output details of the task.
	output := fmt.Sprintf("Started task: task queue(%s), task name(%s), payload(%s)",
		queueName,
		taskName,
		string(body),
	)
	log.Println(output)

	// Get POST data parse the body
	var p Payload
	err1 := json.Unmarshal([]byte(string(body)), &p)
	if err1 != nil {
		log.Printf("Error parsing payload JSON: %v", err1)
		http.Error(w, err1.Error(), http.StatusBadRequest)
		return
	}
	log.Printf("payload: %+v", p)
	i := dsInfo{Kind: p.Ds_kind, Id: p.Ds_id}

	// Execute the indel primer
	setDatastoreStatus(p.Ds_kind, p.Ds_id, "RUNNING", "")
	result, err2 := runIndelPrimer(p, i)
	check(err2, i)
	log.Printf("result: %+v", result)

	setDatastoreStatus(p.Ds_kind, p.Ds_id, "COMPLETE", "")

	if err5 := json.NewEncoder(w).Encode("submitted indel-primer-2"); err5 != nil {
		log.Printf("Error sending response: %v", err5)
	}

	// Set a non-2xx status code to indicate a failure in task processing that should be retried.
	// For example, http.Error(w, "Internal Server Error: Task Processing", http.StatusInternalServerError)

	fmt.Fprintln(w, "200 OK")

}

// indexHandler responds to requests with our greeting.
func indexHandler(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}

	fmt.Fprint(w, "200 OK")
}

func main() {
	http.HandleFunc("/", indexHandler)
	http.HandleFunc("/ip", ipHandler)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("listening on %s", port)
	log.Fatal(http.ListenAndServe(fmt.Sprintf(":%s", port), nil))
}
