# Change Log

--- 

##### v1.5.1 (2020-08-30)

* The [primer indel tool](/tools/pairwise_indel_finder) has been released.

#### v1.5 (2020-08-15)

* The primary data model has moved from isotypes to strains.
* The backend of the site has been substantially restructured to improve maintainability.
* A table of strains with issues has been added to the data releases page.
* The variant data table has been removed from isotype pages.
* New strain collection images have been added.
* The API has been removed. It did not see a lot of usage and become cumbersome to maintain.
* A new [collaborators](/about/collaborators) page has been added.
* Software and Methods have been moved to be per-release, as the pipeline is ever-evolving.
* Data links have been removed from isotype pages; They are still available on the release pages.
* Reports for Alignment, Concordance, And Variant calling are now produced for all releases.
* Publications have been updated.
* The public mappings page was removed as our mapping infrastructure is changing.
* A new tool for calculating [heritability](/tools/heritability) has been released.
* A tool for generating primers for genotyping indels will be released soon.

__Genome Browser__

* IGVjs has been upgraded and has a number of new tools.
* A track for repeat_masker, and Dust data has been added.
* A track for transposons from [_Laricchia et al._ 2017](https://andersenlab.org/publications/2017Laricchia.pdf) been added.
* Tracks for divergent regions from [_Lee et al._ 2020](https://andersenlab.org/publications/2020LeebioRxiv.pdf) have been added.

#### v1.3.4 (2020-02-23)

* Logins now redirect to the previous page.
* Fixed Github authentication issues. A public email is no longer required.

#### v1.3.3 (2020-02-04)

* Fixed Google authentication issues.

#### v1.3.2 (2019-10-20)

* Update Strain map background to ESRI worldmap tileset.
* Add a [publications](/about/publications) page listing publications that have cited CeNDR.
* Fixed a bug that broke the statistics page.
* Updated internal software to improve security.

#### v1.3.1 (2019-02-17)

* Use a natural sort for strain names on global strain map.
* Update software versions.
* Improvements to ordering form.
* Add code of conduct.
* Add issue tracker link.

#### v1.3.0 (2018-10-03)

* Add interval data to reports


#### v1.2.9 (2018-04-15)

* New dataset release: 20180527
* Added collection photos.
* Added variant counts.
* Fixed issue with early reports missing.
* Added variant correlation plot.


#### v1.2.8 (2018-03-18)

* Fix link on data page
* Fix error with ordering

#### v1.2.7 (2018-03-01)

* Fix site error when strain URL not found.
* Fix warning banner for users attempting to access their profile that are not logged in.
* Update sqlite schema.

#### v1.2.6 (2018-02-23)

* Fix error with v1 reports that are not significant.

#### v1.2.5 (2018-02-23)

* Prevent queries on browser from exceeding 100kb and crashing the site.
* Fix v1 report links
* Fix LD plots on v1 reports
* Fix homepage link
* Fix errant API calls on gene pages
* Fix broken link on outreach page.

#### v1.2.4 (2018-02-21)

* Fix issue with the way private reports are organized.

#### v1.2.3 (2018-02-21)

* Fix genome browser URLs.

#### v1.2.2 (2018-02-21)

* Removed extraneous information from v2 report.

#### v1.2.1 (2018-02-21)

* Quick fix for certain v2 reports that would not load properly

#### v1.2.0 (2018-02-21)

__New Pages__

* A statistics page has been added that details strains/isotypes collected over time, visitors over time, and 

__Site Infrastructure__

* Added login system
* Moved codebase to Python 3.
* Improved robustness of forms using python module WTForms.
* Switched database to a single SQLite flatfile + Google Datastore
* Moved BAMs to AWS.

__Mapping Pipeline__

* Moved mapping infrastructure to AWS Fargate
* Added new description field
* The embargo option has been dropped for publishing reports
* Added tooltips to report allele distribution maps.
* Mapping reports have been removed from gene pages. The new database infrastructure makes it difficult to incorporate these.

__Browser__

* Add allele frequency (AF) as column on variant output.
* Added BAMs for strains
* Reorganized variant data table output. Variants that affect multiple transcripts are now grouped together.

__Public Mappings__

* The waffle chart has been removed.

__Data__

* CRAMS files and downloads have been removed.

#### v1.1.2 (2017-12-05)

* Fixed a bug preventing the download button from working properly.

#### v1.1.1 (2017-10-18)

* Fixed Drawing of the Tajimas D plot on report pages.
* Added ability to view all genotypes on the variant viewer

#### v1.1.0 (2017-06-16)

* A revamped genome browser, which offers the ability to download data in a tab-delimited format (TSV).
* The release of a larger set of strains (our 2017-05-31 set). The site now has 249 isotypes available, and a fourth set of strains.
* The Data page has been renamed as the 'releases' page to reflect the fact that our set of genomic data continues to evolve.
* Many other bug-fixes and minor enhancements.

#### v1.0.9 (2017-01-24)

* Released transposon data.

#### v1.0.8 (2016-12-20)

* Fixed issue with ordering page

#### v1.0.7 (2016-12-19)

* Fixed issue with css on strain pages.

#### v1.0.6 (2016-12-03)

* Added additional error checking to mapping submission page.
* Changed submissions to run 'on demand.'

#### v1.0.5 (2016-12-01)

* Fixed an issue with GWA submission.

#### v1.0.4 (2016-11-28)

* Fixed an issue regarding encoding of strain meta info.

#### v1.0.3 (2016-11-18)

* Fixed searching on public mappings.
* Fixed the calendar heatmap on public mappings.
* Fixed caching on reports.
* Updated phenotype histogram to use plotly-js.
* Genotypes are now shown beneath variants on the browser page. We are working on methods for exporting data.

#### v1.0.2 (2016-11-02)

* Fixed an issue that prevented variant correlation tables from being output.

#### v1.0.1 (2016-10-18)

* A change log has been added. You are looking at it.
* A link to the change log was added to the homepage.
* A link to the CeNDR paper and Nucleic Acids Research was added to the homepage.
* Fixed an issue that prevented the phastCons track from showing on the browser.
* Fixed sorting of news items.