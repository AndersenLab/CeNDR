# Generate Thumbnails
Google Cloud Function to monitor isolation photo bucket 
and generate thumbnails when new images are added

# Testing
To test changes to Cloud Functions, you MUST alter the function name BEFORE deploying or you will OVERWRITE the Function in PRODUCTION


# Deploy
Deploy to production with deploy.sh 
Script must be executed from inside the cloud function directory 
(ie: cd cloud_functions/generate_thumbnails; deploy.sh)
