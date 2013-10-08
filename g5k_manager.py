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

logger.setLevel(logging.INFO)

oargrid_job_id = 47185 # -1 for a deploying with a new reservation || > 0 for working with an existing reservation
ssh_key = "/tmp/oargrid/oargrid_ssh_key_dbalouek_"+str(oargrid_job_id)
env = "http://public.nancy.grid5000.fr/~dbalouek/ens/debian/wheezy-x64-diet.dsc"
walltime = '01:00:00'
n_nodes = 2
oargridsub_opts = '-t deploy'
nodes_perf = "./nodes_perf"
nodes_green ="./nodes_green"
nodes_service = "./nodes_service"
nodefile = "./gridnodes-uniq"
try:
    os.remove(nodes_perf); os.remove(nodes_service); os.remove(nodes_green);
except OSError:
    pass

sites = []
hosts_perf = {'cluster' : 'sagittaire', 'number' : n_nodes}
hosts_green = {'cluster' : 'sagittaire', 'number' : n_nodes}
hosts_service = {'cluster' : 'sagittaire', 'number' : 2} # MA + Client

site = get_cluster_site(hosts_service["cluster"])
user_frontend_connexion_params={'user': 'dbalouek', 'default_frontend': "lyon", 'ssh_options': ('-tt', '-o', 'BatchMode=yes', '-o', 'PasswordAuthentication=no', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', '-o', 'ConnectTimeout=45')}
root_connexion_params={'user': 'root', 'ssh_options': ('-tt', '-o', 'BatchMode=yes', '-o', 'PasswordAuthentication=no', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', '-o', 'ConnectTimeout=45')}

logger.info("Job Submission...")
subs = []
sub_resources=''
for hosts in [hosts_perf,hosts_service,hosts_green]:
    sub_resources += "{cluster=\\'"+hosts["cluster"]+"\\'}/nodes="+str(hosts["number"])+'+'
subs.append((OarSubmission(resources=sub_resources[:-1]),site))
 
nodes = [] 

if oargrid_job_id < 0:
    job = oargridsub(subs, walltime = walltime, additional_options = oargridsub_opts)
    oargrid_job_id = job[0]
    ssh_key = job[1]
    
    if oargrid_job_id < 0:
        print oargrid_job_id
        logger.info("No ressources availables")
        logger.info("End of program")
        sys.exit(0)
        
    logger.info("Wait for job to start...")
    wait_oargrid_job_start(oargrid_job_id)

logger.info("Wait for job to start...")
wait_oargrid_job_start(oargrid_job_id)
print oargrid_job_id
print ssh_key 
nodes = get_oargrid_job_nodes(oargrid_job_id)
logger.info("Job has started")
 
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
writeNodesToFile(nodes, nodefile)
    

# We now write the nodes in files (useful for diet operations)
nodes = getNodesfromFile(nodefile)
writeNodesToFile(nodes,"./dietg/gridnodes")
writeNodesToFile(nodes,"./dietg/gridnodes-uniq")
writeNodesToFile(nodes,"./gridnodes")
writeNodesToFile(nodes,"./gridnodes-uniq")

# We now write the nodes in files (useful for diet operations)
nb_hosts_perf = 0
nb_hosts_green = 0
nb_hosts_service = 0
for node in nodes:
    if hosts_perf["cluster"] in node and nb_hosts_perf < hosts_perf["number"]:
        logger.debug("%s / perf",node)
        with open(nodes_perf, "a") as file1:
            file1.write(node)
            file1.write("\n")
            file1.close()
            nb_hosts_perf += 1
    elif hosts_green["cluster"] in node and nb_hosts_green < hosts_green["number"]:
        logger.debug("%s / green",node)
        with open(nodes_green, "a") as file1:
            file1.write(node)
            file1.write("\n")
            file1.close()
            nb_hosts_green += 1
    elif hosts_service["cluster"] in node and nb_hosts_service < hosts_service["number"]:
        with open(nodes_service, "a") as file1:
            logger.debug("%s / service",node)
            file1.write(node)
            file1.write("\n")
            file1.close()
            nb_hosts_service += 1

if file_len(nodes_perf) != hosts_perf["number"] or file_len(nodes_service) != hosts_service["number"] or file_len(nodes_green) != hosts_green["number"] :
        logger.info("The number of nodes in files mismatch the desired resources")
        logger.info("End of program")
        sys.exit(0)
        
params_diet = {}
params_diet["site"] = site
params_diet["scheduler"] = "PERF"
params_diet["concLimit"] = "1"
params_diet["useRate"] = "50.0"
total_time = 0

mydiet = DietDeploy(params_diet)

results = {}
     
mydiet.clean_archi()
 
mydiet.create_archi_files()
   
mydiet.retrieve_agents()
  
mydiet.update_frontend()
     
mydiet.update_nodes()
 
mydiet.stop_archi()

time.sleep(5)
mydiet.start_MA()
time.sleep(5)
mydiet.start_servers()
time.sleep(5)



