from execo import configuration, logger, Put, Process, Remote
from execo.log import set_style
from execo_g5k.oar import format_oar_date
from execo_g5k import get_oar_job_nodes, OarSubmission, oargridsub, get_oargrid_job_nodes, wait_oargrid_job_start, get_oargrid_job_oar_jobs, get_oar_job_kavlan, oargriddel, deploy, Deployment
from execo_g5k.api_utils import get_host_site,get_cluster_site, get_g5k_sites, get_g5k_clusters, get_resource_attributes, get_host_attributes, get_cluster_attributes, get_site_clusters

import logging
import time
import os
import sys
from pprint import pprint
from diet_deploy import DietDeploy, getNodesfromFile
from diet_utils import get_results, get_node_name, writeNodesToFile, file_len

logger.setLevel(logging.DEBUG)

oargrid_job_id = -1 # -1 for a deploying with a new reservation || > 0 for working with an existing reservation
ssh_key = "/tmp/oargrid/oargrid_ssh_key_dbalouek_"+str(oargrid_job_id)
env = "http://public.nancy.grid5000.fr/~dbalouek/ens/debian/wheezy-x64-diet.dsc"
walltime = '01:00:00'
n_nodes = 4
oargridsub_opts = '-t deploy'
mode = "prod"

clusters_perf = ['sagittaire']
clusters_green = ['sagittaire']
clusters_service = ["sagittaire"]

site = get_cluster_site(clusters_service[0])
frontend = site+".grid5000.fr"
user_frontend_connexion_params={'user': 'dbalouek', 'default_frontend': site, 'ssh_options': ('-tt', '-o', 'BatchMode=yes', '-o', 'PasswordAuthentication=no', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', '-o', 'ConnectTimeout=45')}
root_connexion_params={'user': 'root', 'ssh_options': ('-tt', '-o', 'BatchMode=yes', '-o', 'PasswordAuthentication=no', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', '-o', 'ConnectTimeout=45')}

if oargrid_job_id == -1:
# New reservation

    sites = []
       
    #Pick a perf cluster
    for cluster in clusters_perf:
        cl_site = get_cluster_site(cluster)
        if cl_site not in sites:
            sites.append(cl_site)
     
    #Pick a green cluster
    for cluster in clusters_green:
        cl_site = get_cluster_site(cluster)
        if cl_site not in sites:
            sites.append(cl_site)
             
    #Pick a service cluster
    for cluster in clusters_service:
        cl_site = get_cluster_site(cluster)
        if cl_site not in sites:
            sites.append(cl_site)
     
    resources = {}
    for cluster in clusters_perf:
        resources[cluster] = n_nodes #
    for cluster in clusters_green:
        resources[cluster] = n_nodes #
    for cluster in clusters_service:
        resources[cluster] = 2 # MA + Client Only (Use more if you want MA + 2 LA,etc ...)
     
     
    logger.info("Job Submission...")
    subs = []
    for s in sites:
        sub_resources=''
        for cluster in get_site_clusters(s):
            if resources.has_key(cluster):
                sub_resources += "{cluster=\\'"+cluster+"\\'}/nodes="+str(resources[cluster])+'+'
        subs.append((OarSubmission(resources=sub_resources[:-1]),s))
     
    job = oargridsub(subs, walltime = walltime, additional_options = oargridsub_opts)
    oargrid_job_id = job[0]
    ssh_key = job[1]
    
    if oargrid_job_id < 0:
        print oargrid_job_id
        logger.info("No ressources availables")
        logger.info("End of program")
        sys.exit(0)
        
if oargrid_job_id > 0:
# Working on a valid reservation
     
    logger.info("Wait for job to start...")
    print oargrid_job_id
    print ssh_key
     
    nodes = []
    wait_oargrid_job_start(oargrid_job_id)
    nodes = get_oargrid_job_nodes(oargrid_job_id)
     
    print nodes
     
    logger.info("Deployment started")
    nodes = deploy(Deployment(hosts = nodes, env_file = "http://public.nancy.grid5000.fr/~dbalouek/envs/debian/wheezy-x64-diet.dsc", user = "dbalouek"))
    deploy_nodes = nodes[0]   
    ko_nodes = nodes[1]
    logger.info("Deployment completed")
     
    if not deploy_nodes:
        logger.info("No nodes were correctly deployed")
        logger.info("End of program")
        sys.exit(0)
     
    #Get the "clean" list of nodes
    nodes = []
    for host in deploy_nodes:
        nodes.append(get_node_name(host))
        logger.debug("%s",host)
# End if
