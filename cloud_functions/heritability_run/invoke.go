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
	"time"

	"cloud.google.com/go/datastore"
	"cloud.google.com/go/storage"
)

// change to v2 20210121
const heritabilityVersion = "v2"
const datasetName = "data.tsv"
const resultName = "result.tsv"
const bucketName = "elegansvariation.org"
const projectID = "andersen-lab"

type Payload struct {
	Hash    string
	Ds_id   string
	Ds_kind string
}

type dsInfo struct {
	Kind string
	Id   string
}

type dsEntry struct {
	Username    string
	Label       string
	Data_hash   string
	Status      string
	Modified_on time.Time
	Created_on  time.Time
	K           *datastore.Key `datastore:"__key__"`
}

func check(e error, i dsInfo) {
	if e != nil {
		setDatastoreStatus(i.Kind, i.Id, "ERROR")
		panic(e)
	}
}

func setDatastoreStatus(kind string, id string, status string) {
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

	if _, err := dsClient.Put(ctx, k, e); err != nil {
		log.Fatal(err)
	}

	fmt.Printf("Updated status msg: %q\n", e.Status)
}

func downloadFile(w io.Writer, object string) ([]byte, error) {
	// object := "object-name"
	ctx := context.Background()
	client, err := storage.NewClient(ctx)
	if err != nil {
		return nil, fmt.Errorf("storage.NewClient: %v", err)
	}
	defer client.Close()

	ctx, cancel := context.WithTimeout(ctx, time.Second*50)
	defer cancel()

	rc, err := client.Bucket(bucketName).Object(object).NewReader(ctx)
	if err != nil {
		return nil, fmt.Errorf("Object(%q).NewReader: %v", object, err)
	}
	defer rc.Close()

	data, err := ioutil.ReadAll(rc)
	if err != nil {
		return nil, fmt.Errorf("ioutil.ReadAll: %v", err)
	}
	fmt.Fprintf(w, "Blob %v downloaded.\n", object)
	return data, nil
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

func runTask(dataHash string, queueName string, taskName string, i dsInfo) {
	// Run the heritability analysis. This is used to run it in the background.
	// Execute R script
	cmd := exec.Command("Rscript", "H2_script.R", datasetName, resultName, "hash.txt", heritabilityVersion, "strain_data.tsv")
	cmd.Stderr = os.Stderr
	o, err := cmd.Output()
	check(err, i)

	// Copy results to google storage.
	resultBlob := fmt.Sprintf("reports/heritability/%s/%s", dataHash, resultName)
	copyBlob(bucketName, resultName, resultBlob, i)

	// Log & output details of the task.
	output := fmt.Sprintf("Completed task: task queue(%s), task name(%s), output(%s)",
		queueName,
		taskName,
		o,
	)
	log.Println(output)
}

func h2Handler(w http.ResponseWriter, r *http.Request) {
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

	// Download the dataset
	dataBlob := fmt.Sprintf("reports/heritability/%s/%s", p.Hash, datasetName)
	dataset, err2 := downloadFile(os.Stdout, dataBlob)
	check(err2, i)

	// Store it locally
	f, err3 := os.Create(datasetName)
	check(err3, i)
	f.Write(dataset)
	f.Close()

	// Write the hash
	h, err4 := os.Create("hash.txt")
	check(err4, i)
	h.WriteString(p.Hash + "\n")
	f.Close()

	// Log & output details of the task.
	output := fmt.Sprintf("Started task: task queue(%s), task name(%s), payload(%s)",
		queueName,
		taskName,
		string(body),
	)
	log.Println(output)

	// Update datastore
	setDatastoreStatus(p.Ds_kind, p.Ds_id, "RUNNING")

	// Execute the R script
	runTask(p.Hash, queueName, taskName, i)

	setDatastoreStatus(p.Ds_kind, p.Ds_id, "COMPLETE")

	if err5 := json.NewEncoder(w).Encode("submitted h2"); err5 != nil {
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
	http.HandleFunc("/h2", h2Handler)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("listening on %s", port)
	log.Fatal(http.ListenAndServe(fmt.Sprintf(":%s", port), nil))
}
