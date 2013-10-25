from execo import configuration, logger, Put, Process, Remote
#from execo.log import set_style
from execo_g5k.oar import format_oar_date
from execo_g5k import get_oar_job_nodes, OarSubmission, oargridsub, get_oargrid_job_nodes, wait_oargrid_job_start, get_oargrid_job_oar_jobs, get_oar_job_kavlan, oargriddel, deploy, Deployment
from execo_g5k.api_utils import get_host_site,get_cluster_site, get_g5k_sites, get_g5k_clusters, get_resource_attributes, get_host_attributes, get_cluster_attributes, get_site_clusters

import logging
import time
import os
import sys
from pprint import pprint

from execo import configuration, logger, Put, Process, Remote, Get, Host
from execo_g5k import get_host_attributes, get_site_attributes, APIConnection
import shutil
import logging
import os
import ast
import pprint
from datetime import datetime
import json
import matplotlib.pyplot as plt

logger.setLevel(logging.INFO)

def writeNodesToFile(inputList, outputFile):
    a = open(outputFile, "w")
    listLength = len(inputList)
    for i in range(0,listLength):
        a.write(str(inputList[i])+"\n")
    a.close()
    
def file_len(inputFile):
    num_lines = sum(1 for line in open(inputFile))
    return num_lines

# def push_sched_to_node(nodes):
#     logger.info("Update sched folder on frontend...")
#     os.system("make clean; rsync -avz ~/dev/diet_execo/dietg/diet-sched-example bordeaux.g5k:/home/dbalouek/dietg/")
#     logger.info("Sent")
#     logger.info("Update sched folder on nodes...")
#     cmd = "cd /home/dbalouek/dietg/; ./update_sched_directory.sh"
#     a = Remote(cmd,[frontend],connexion_params = user_frontend_connexion_params).run()
#     logger.info("Done!")
#     
    
def get_node_name(host):
    for netadap in get_host_attributes(host)['network_adapters']: 
        if netadap.has_key('network_address'):
            return  netadap['network_address']


def getNodesfromFile(inputFile):
    res = [line.split() for line in open(inputFile).readlines()]
    nodes = []
    for host in res:
        nodes += host
    return nodes

def set_scheduler(inputFileName, scheduler, custom_value = 1):
    custom_value = str(custom_value)
    scheduler_template = "./dietg/diet-sched-example/myscheduler.hh_t"
    scheduler_instance = "./dietg/diet-sched-example/myscheduler.hh"
    
    try:
        os.remove(scheduler_instance);
    except OSError:
        pass
    
    process = Process("cp "+scheduler_template+" "+scheduler_instance)
    process.run()
    cmd = "./dietg/set_scheduler_criteria.sh "+scheduler
    print cmd
    cmd = "sed -i 's/<<criteria>>/"+scheduler+"/g' "+scheduler_instance
    process = Process(cmd)
    process.run()
    cmd = "sed -i 's/<<value>>/"+custom_value+"/g' "+scheduler_instance
    process = Process(cmd)
    process.run()
    scheduler_path="schedulerModule =/root/dietg/diet-sched-example/myscheduler.so\n"
    
    with open(inputFileName, "a") as MAcfg:
        MAcfg.write(scheduler_path)
        MAcfg.close()
    
def set_parallel_jobs(inputFileName,limit):
    
    use_limit = "useConcJobLimit = true"+"\n"
    value_limit = "maxConcJobs = "+limit+"\n"
    print inputFileName
    with open(inputFileName, "a") as SeDcfg:
        SeDcfg.write(use_limit)
        SeDcfg.write(value_limit)
        SeDcfg.close()
    
def get_g5k_api_measures(node_name,site_name,metric,start_timestamp,end_timestamp,resolution):
    """ Return a dict with the api values"""
    
    start_date = datetime.fromtimestamp(float(start_timestamp)).strftime('%Y-%m-%d %H:%M:%S')
    end_date = datetime.fromtimestamp(float(end_timestamp)).strftime('%Y-%m-%d %H:%M:%S')
    
    logger.debug("Get %s from %r to %r on %s",node_name,start_date,end_date,node_name)
    request = "sites/"+site_name+"/metrics/"+metric+"/timeseries/"+node_name+"?resolution="+str(resolution)+"&from="+str(start_timestamp)+"&to="+str(end_timestamp)
    
    #curl -k "https://api.grid5000.fr/2.1/grid5000/sites/lyon/metrics/pdu/timeseries/taurus-3?resoltuion=15&from=1370205024&to=1370205400"
    
    logger.debug("API Request = %s",request)
    attr = APIConnection()
    response = attr.get(request)
    
    # Convert the result as a dict
#     print response
    tuple = ast.literal_eval(str(response))
    
#     print type(tuple)
#     print len(tuple)
    res = tuple[1]
    
    #Parsing of the JSON data
    obj = json.loads(res)
    
    values = obj["values"]
    values = [x for x in values if type(x) == float]
    
#     print values
#     print len(values)
#     
    mean = reduce(lambda x, y: x + y, values) / len(values)
    return mean

def get_results(results_object,diet_object):
    res = results_object
    print res["nbsed"]
    print "Conso:"
    
def get_nb_tasks(inputFile):
    """ The number of lines is equal to the number of lines in the file"""
    nb_tasks = 0;
    try:
        res = [line.split() for line in open(inputFile).readlines()]
        for host in res:
            nb_tasks += 1
    except IOError:
        print 'Oh dear. No tasks file on node!'
        nb_tasks = -1
    return nb_tasks

def save_results():
    print "TO DO!"