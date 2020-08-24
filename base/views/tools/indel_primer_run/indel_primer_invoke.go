package main

// VERSION v1

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path"

	"cloud.google.com/go/storage"
)

const vcfURL = "http://storage.googleapis.com/elegansvariation.org/tools/pairwise_indel_primer/WI.HARD_FILTERED.FP.vcf.gz"
const datasetName = "results.tsv"
const resultName = "data.json"

func check(e error) {
	if e != nil {
		panic(e)
	}
}

func DownloadFile(filepath string, url string) error {

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

func runIndelPrimer(w http.ResponseWriter, r *http.Request) {
	/*
		Runs the herritability analysis
	*/

	// Run the heritability analysis. This is used to run it in the background.
	// Execute R script

	site := r.FormValue("site")
	dataHash := r.FormValue("hash")
	strain1 := r.FormValue("strain1")
	strain2 := r.FormValue("strain2")

	// Download Index
	indexURL := fmt.Sprintf("%s.csi", vcfURL)
	DownloadFile(path.Base(indexURL), indexURL)

	fmt.Printf("vk primer indel --region %v --ref=WS276 --samples=%v %v", site, fmt.Sprintf("%s,%s", strain1, strain2), vcfURL)
	cmd := exec.Command("vk", "primer", "indel", "--region", site, "--ref", "WS276", "--samples", fmt.Sprintf("%s,%s", strain1, strain2), vcfURL)

	cmd.Stderr = os.Stderr
	_, err := cmd.Output()
	check(err)
	fmt.Println(err)

	// Copy results to google storage.
	resultBlob := fmt.Sprintf("reports/indel_primer/%s/data.json", dataHash, resultName)
	copyBlob("elegansvariation.org", resultName, resultBlob)

	if err := json.NewEncoder(w).Encode("submitted h2"); err != nil {
		log.Printf("Error sending response: %v", err)
	}

}

func main() {

	http.HandleFunc("/", runIndelPrimer)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("listening on %s", port)
	log.Fatal(http.ListenAndServe(fmt.Sprintf(":%s", port), nil))
}
