#!

#library(rdatastore)
library(devtools)

# Output session info
devtools::session_info()

# Get commit of git and version
path = find.package('cegwas')

# Get variables
REPORT_NAME <- Sys.getenv('REPORT_NAME')
TRAIT_NAME <- Sys.getenv('TRAIT_NAME')
GOOGLE_APPLICATION_CREDENTIALS <- Sys.getenv('GOOGLE_APPLICATION_CREDENTIALS')


#rdatastore::authenticate_datastore_service('gcloud-project.json', 'andersen-lab')