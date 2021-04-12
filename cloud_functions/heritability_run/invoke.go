package main

// VERSION v1

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

	"cloud.google.com/go/storage"
)

// change to v2 20210121
const heritabilityVersion = "v2"
const datasetName = "data.tsv"
const resultName = "result.tsv"
const bucketName = "elegansvariation.org"

type Payload struct {
	Hash string
}

func check(e error) {
	if e != nil {
		panic(e)
	}
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

func copyBlob(bucket string, source string, blob string) {
	log.Printf("%s --> %s", source, blob)
	ctx := context.Background()
	client, err := storage.NewClient(ctx)
	check(err)

	// source
	f, err := os.Open(source)
	if err != nil {
		log.Fatal(err)
	}
	defer f.Close()

	wc := client.Bucket(bucket).Object(blob).NewWriter(ctx)
	_, err = io.Copy(wc, f)
	check(err)
	err = wc.Close()
	check(err)
}

func fileExists(filename string) bool {
	info, err := os.Stat(filename)
	if os.IsNotExist(err) {
		return false
	}
	return !info.IsDir()
}

func runTask(dataHash string, queueName string, taskName string) {
	// Run the heritability analysis. This is used to run it in the background.
	// Execute R script
	cmd := exec.Command("Rscript", "H2_script.R", datasetName, resultName, "hash.txt", heritabilityVersion, "strain_data.tsv")
	cmd.Stderr = os.Stderr
	o, err := cmd.Output()
	check(err)

	// Copy results to google storage.
	resultBlob := fmt.Sprintf("reports/heritability/%s/%s", dataHash, resultName)
	copyBlob(bucketName, resultName, resultBlob)

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
		log.Printf("Error parsing payload JSON: %v", err)
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	log.Printf("payload: %+v", p)

	// Download the dataset
	dataBlob := fmt.Sprintf("reports/heritability/%s/%s", p.Hash, datasetName)
	dataset, err2 := downloadFile(os.Stdout, dataBlob)
	check(err2)

	// Store it locally
	f, err3 := os.Create(datasetName)
	check(err3)
	f.Write(dataset)
	f.Close()

	// Write the hash
	h, err4 := os.Create("hash.txt")
	check(err4)
	h.WriteString(p.Hash + "\n")
	f.Close()

	// Log & output details of the task.
	output := fmt.Sprintf("Started task: task queue(%s), task name(%s), payload(%s)",
		queueName,
		taskName,
		string(body),
	)
	log.Println(output)

	// Execute the R script
	runTask(p.Hash, queueName, taskName)

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
