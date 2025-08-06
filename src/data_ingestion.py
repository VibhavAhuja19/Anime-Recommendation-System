import os
import pandas as pd
from google.cloud import storage
from google.oauth2 import service_account
from src.logger import get_logger
from src.custom_exception import CustomException
from config.path_config import *
from utils.common_functions import read_yaml
import sys
import traceback
 
logger = get_logger(__name__)

class DataIngestion:
    def __init__(self, config):
        self.config = config["data_ingestion"]
        self.bucket_name = self.config["bucket_name"]
        self.file_names = self.config["bucket_file_names"]
        self.service_account_key = self.config["service_account_key_path"]
        os.makedirs(RAW_DIR, exist_ok=True)
        logger.info(f"Data Ingestion Started. Files will be saved to: {RAW_DIR}")

    def _get_gcp_client(self):
        """Authenticate with GCP using service account credentials"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_key,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            return storage.Client(credentials=credentials)
        except Exception as e:
            logger.error(f"Failed to authenticate with GCP: {str(e)}")
            raise CustomException("GCP authentication failed", sys)

    def download_csv_from_gcp(self):
        try:
            client = self._get_gcp_client()
            bucket = client.bucket(self.bucket_name)

            for file_name in self.file_names:
                file_path = os.path.join(RAW_DIR, file_name)
                logger.info(f"Attempting to download {file_name} to {file_path}")

                try:
                    blob = bucket.blob(file_name)
                    if not blob.exists():
                        raise FileNotFoundError(f"File {file_name} not found in bucket")
                    
                    blob.download_to_filename(file_path)
                    logger.info(f"Successfully downloaded {file_name}")

                    if file_name == "animelist.csv":
                        try:
                            data = pd.read_csv(file_path, nrows=5000000)
                            data.to_csv(file_path, index=False)
                            logger.info("Large file processed - limited to 5M rows")
                        except Exception as e:
                            logger.error(f"Error processing large file: {str(e)}")
                            raise

                except Exception as e:
                    logger.error(f"Error downloading {file_name}: {str(e)}")
                    raise CustomException(f"Failed to download {file_name}", sys)

        except Exception as e:
            logger.error(f"Error while downloading data from GCP: {str(e)}")
            raise CustomException("Failed to download data from GCP", sys)
        
    def run(self):
        try:
            logger.info("Starting Data Ingestion Process...")
            self.download_csv_from_gcp()
            logger.info("Data Ingestion Completed Successfully")
        except CustomException as ce:
            logger.error(f"CustomException occurred: {str(ce)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise CustomException("Data ingestion failed", sys)

if __name__ == "__main__":
    try:
        config = read_yaml(CONFIG_PATH)
        data_ingestion = DataIngestion(config)
        data_ingestion.run()
    except Exception as e:
        logger.error(f"Fatal error in data ingestion: {str(e)}")
        raise