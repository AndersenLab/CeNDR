---
title: API Reference

language_tabs: # must be one of https://git.io/vQNgJ
  - shell
  - r
  - python

toc_footers:
  - <a href='#'>Sign Up for a Developer Key</a>
  - <a href='https://github.com/lord/slate'>Documentation Powered by Slate</a>

includes:
  - errors

search: true
---

# Introduction

Welcome to CeNDR API Documentation! CeNDR has an easy to use API and can be used to retrieve data on strains and genetic data.

# Strains and Isotypes

## Fetch information on strains

```python
import requests

# Fetch a single strain (dict)
data = requests.get("http://elegansvariation.org/api/strain/AB1")
data.json()

# Fetch a list of all strains (list)
data = requests.get("http://elegansvariation.org/api/strain/")
data.json()

# Fetch a list of strains of a given isotype (list)
data = requests.get("http://elegansvariation.org/api/strain/isotype/CB4856")
data.json()

# Fetch list of all reference strains (one strain for each isotype)
data = requests.get("http://elegansvariation.org/api/strain/isotype")
data.json()

```

```r
library(httr)
library(jsonlite)
library(tidyverse)


# Fetch a single strain (list)
single_strain <- httr::GET("http://localhost:5000/api/strain/AB1") %>%
                 httr::content()

# Fetch a list of all strains and convert it to a dataframe (tibble/dataframe)
data <- httr::GET("http://localhost:5000/api/strain/") %>%
        httr::content(., "text", encoding='UTF-8') %>%
        jsonlite::fromJSON() %>%
        dplyr::tbl_df()

# Fetch a list of all strains of a given isotype and convert it to a dataframe (tibble/dataframe)
data <- httr::GET("http://localhost:5000/api/strain/isotype/CB4856") %>%
        httr::content(., "text", encoding='UTF-8') %>%
        jsonlite::fromJSON() %>%
        dplyr::tbl_df()

# Fetch a list of all isotypes and convert it to a dataframe (tibble/dataframe)
data <- httr::GET("http://localhost:5000/api/strain/isotype/") %>%
        httr::content(., "text", encoding='UTF-8') %>%
        jsonlite::fromJSON() %>%
        dplyr::tbl_df()
```

```shell
# Fetch a single strain
curl https://elegansvariation.org/api/strain/CB4856

# Fetch a list of all strains
curl https://elegansvariation.org/api/strain

# Fetch a list of all strains belonging to a given isotype
curl https://elegansvariation.org/api/strain/isotype/CB4856

# Fetch a list of all all isotypes
curl https://elegansvariation.org/api/isotype/
```


> The above commands returns JSON structured like this:

```json
# /api/strain - Returns a list of all strains.
# /api/strain/isotype/CB4856 - Returns list of strains belonging to an isotype.
# /api/isotype - Returns list of all isotypes (one reference strain/isotype).
[
  {
    "elevation": 40.96225357055664,
    "isolated_by": "D. Riddle & A. Bird",
    "isolation_date": "1983-01-01",
    "isolation_date_comment": "only year (1983) is known",
    "isotype": "AB1",
    "landscape": null,
    "latitude": -34.93,
    "longitude": 138.59,
    "notes": "Tc1 pattern VII",
    "photo": null,
    "previous_names": null,
    "reference_strain": true,
    "release": 20160408,
    "sampled_by": "D. Riddle & A. Bird",
    "sets": "2",
    "source_lab": "CGC",
    "strain": "AB1",
    "substrate": "Soil"
    },
    { ... }
]

# /api/strain/AB1 - Returns dictionary of single strain

{
    "elevation": 40.96225357055664,
    "isolated_by": "D. Riddle & A. Bird",
    "isolation_date": "1983-01-01",
    "isolation_date_comment": "only year (1983) is known",
    "isotype": "AB1",
    "landscape": null,
    "latitude": -34.93,
    "longitude": 138.59,
    "notes": "Tc1 pattern VII",
    "photo": null,
    "previous_names": null,
    "reference_strain": true,
    "release": 20160408,
    "sampled_by": "D. Riddle & A. Bird",
    "sets": "2",
    "source_lab": "CGC",
    "strain": "AB1",
    "substrate": "Soil"
}

```

These endpoints can be used to retrieve information on strains and isotypes.

### HTTP Request


#### `GET http://elegansvariation.org/api/strain/`

Fetch a list of all strains.

<br />

#### `GET http://elegansvariation.org/api/strain/<strain>`

Fetch information on a single strain.

<br />

#### `GET http://elegansvariation.org/api/strain/isotype/<isotype>`

Fetch a list of all strains belonging to an isotype.

<br />

#### `GET http://elegansvariation.org/api/isotype/`

Fetch the complete list of isotypes; For each isotype the reference strain is listed.

### Query Parameters

Parameter | Description
--------- |  -----------
strain |  Name of strain
isotype | Name of isotype



# Genes

## Lookup Gene

```python
import requests

data = requests.get("http://localhost:5000/api/gene/lookup/pot-2")
data.json()
```

```r
library(httr)
library(tidyverse)

gene <- httr::GET("http://localhost:5000/api/gene/lookup/pot-2") %>%
        httr::content()
```

```shell
curl https://elegansvariation.org/api/gene/lookup/pot-2
```

> The above commands returns JSON structured like this:

```json
{
  "chrom": "II", 
  "chrom_num": 2, 
  "start": 14524173
  "end": 14525112, 
  "locus": "pot-2", 
  "gene_symbol": "pot-2", 
  "gene_id": "WBGene00010195", 
  "biotype": "protein_coding", 
  "gene_id_type": "Gene", 
  "sequence_name": "F57C2.3", 
  "arm_or_center": "arm", 
}
```

### HTTP Request

#### `GET http://elegansvariation.org/api/gene/lookup/<gene>`

Fetch a list of all strains.

### Query Parameters

Parameter | Description
--------- |  -----------
gene |  Gene name

## Search for Gene

```python
import requests

data = requests.get("http://localhost:5000/api/gene/search/pot")
data.json()
```

```r
library(httr)
library(tidyverse)

gene <- httr::GET("http://localhost:5000/api/gene/search/pot") %>%
        httr::content()
```

```shell
curl https://elegansvariation.org/api/gene/search/pot
```

> The above commands returns JSON structured like this:

```json
[
  {
    "arm_or_center": "arm", 
    "biotype": "protein_coding", 
    "chrom": "II", 
    "chrom_num": 2, 
    "end": 14525112, 
    "gene_id": "WBGene00010195", 
    "gene_id_type": "Gene", 
    "gene_symbol": "pot-2", 
    "locus": "pot-2", 
    "sequence_name": "F57C2.3", 
    "start": 14524173
  },
  { ... }
]
```

### HTTP Request

#### `GET http://elegansvariation.org/api/gene/search/<query>`

Fetch a list of genes that match a query. The API will look at the locus name, wormbase ID, and sequence name.

### Query Parameters

Parameter | Description
--------- |  -----------
query |  Search term


## Query gene homologs

```python
import requests

# Fetch a single strain (dict)
data = requests.get("http://localhost:5000/api/gene/homolog/HEXB")
data.json()
```

```r
library(httr)
library(tidyverse)


# Fetch a single strain (list)
gene <- httr::GET("http://localhost:5000/api/gene/homolog/HEXB") %>%
        httr::content()
```

```shell
# Fetch a single strain
curl http://localhost:5000/api/gene/homolog/HEXB
```

> The above commands returns JSON structured like this:

```json
[
  {
    "chrom": "X", 
    "chrom_num": 6, 
    "start": 2221150
    "end": 2226620, 
    "locus": "hex-1", 
    "arm_or_center": "arm", 
    "biotype": "protein_coding", 
    "gene_id": "WBGene00020509", 
    "gene_id_type": "Gene", 
    "gene_name": "hex-1", 
    "gene_summary": null, 
    "gene_symbol": "hex-1", 
    "homolog_gene": "HEXB", 
    "homolog_source": "Homologene", 
    "homolog_species": "Homo sapiens", 
    "homolog_taxon_id": 9606, 
    "sequence_name": "T14F9.3", 
  }, 
  { ... }
]
```

### HTTP Request

#### `GET http://elegansvariation.org/api/gene/lookup/<query>`

Fetch a list of all strains.

### Query Parameters

Parameter | Description
--------- |  -----------
query |  This is the name of a homolog in another species (not C. elegans)

