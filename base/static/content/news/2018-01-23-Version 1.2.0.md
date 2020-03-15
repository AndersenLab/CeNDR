#### January 2018 CeNDR Updates

Version 1.2.0 brings many updates to the site.

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