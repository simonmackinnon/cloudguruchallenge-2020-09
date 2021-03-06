import argparse
import boto3
import logging
import numpy
import os
import pandas
import requests
import shutil
import transform
import load

from datetime import datetime, timedelta

logger = logging.getLogger()

def setupLogger(loggerLevel):
    global logger
    logger.setLevel(loggerLevel)
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=loggerLevel,
        datefmt='%d-%m-%Y %H:%M:%S')
    
def getRemoteFile(url, name):
    if not os.path.exists('/tmp/download/'):
        logger.info('Making dir: /tmp/download/')
        os.makedirs('/tmp/download/')
    
    logger.info('downloading: ' + url)
    response = requests.get(url)
    content = response.content
    csv_file = open('/tmp/download/'+name+'.csv', 'wb')
    csv_file.write(content)
    csv_file.close()
    return csv_file.name
            
def cleanupFiles(directory):
    logger.info('Cleaning up: ' + directory)
    shutil.rmtree(directory)

def tableIsEmpty(response):
    return response['Count'] == 0
    
def getLatestRecordDate(response):
    if not tableIsEmpty(response):
        items = response['Items']
        items.sort(key=lambda x: x['date'], reverse=True)
        logger.info('latest date entered in DB: {}'.format(items[0]['date']))
        return(items[0]['date'])
    else:
        return(None)

def getTableScanResponse(table_name, dynamodb_resource):
    table = dynamodb_resource.Table(table_name)
    response = table.scan()
    return response

def main(args):
    usaCovidDataUrl = args['usaCovidDataUrl']
    johnHopkinsDataUrl = args['johnHopkinsDataUrl']
    loggerLevel = logging.__dict__[args['loggerLevel']]
    
    dynamodb_resource = boto3.resource('dynamodb', region_name='ap-southeast-2')
    
    try: 
        setupLogger(loggerLevel)
        logger.info('Starting...')
        usaCovidDataFilename = getRemoteFile(usaCovidDataUrl, 'usaCovidData')
        johnHopkinsRecoveryDataFilename = getRemoteFile(johnHopkinsDataUrl, 'johnHopkinsData')
        mergedData = transform.mergeCsvFiles(usaCovidDataFilename, johnHopkinsRecoveryDataFilename)
        scanResponse = getTableScanResponse('covidData', dynamodb_resource)
        latestDate = getLatestRecordDate(scanResponse)
        intialLoad = tableIsEmpty(scanResponse)
        load.load_data(mergedData, latestDate, dynamodb_resource, intialLoad)
        logger.info('Done!')
    except:
        logger.exception('Error in processing!')
    finally:
        if os.path.isdir('/tmp/download/'):
            cleanupFiles('/tmp/download/')
 
def event_handler(event, context):
    args = dict()
    args['loggerLevel'] = os.environ['LOGGER_LEVEL'] if os.environ['LOGGER_LEVEL'] else 'INFO'
    args['usaCovidDataUrl'] = os.environ['USA_COVID_DATA_URL'] if os.environ['USA_COVID_DATA_URL'] else "https://raw.githubusercontent.com/nytimes/covid-19-data/master/us.csv"
    args['johnHopkinsDataUrl'] = os.environ['JOHN_HOPKINS_DATA_URL'] if os.environ['JOHN_HOPKINS_DATA_URL'] else "https://raw.githubusercontent.com/datasets/covid-19/master/data/time-series-19-covid-combined.csv?opt_id=oeu1601336451462r0.5279466816848477"
    
    logger.info('Args: {}'.format(args))
    
    main(args)      
        
if __name__ == '__main__':
    args = dict()
    args['loggerLevel'] = 'INFO'
    args['usaCovidDataUrl'] = "https://raw.githubusercontent.com/nytimes/covid-19-data/master/us.csv"
    args['johnHopkinsDataUrl'] = "https://raw.githubusercontent.com/datasets/covid-19/master/data/time-series-19-covid-combined.csv?opt_id=oeu1601336451462r0.5279466816848477"
    
    main(args)

