from execo import configuration, logger, Put, Process, Remote
#from execo.log import set_style
from execo_g5k.oar import format_oar_date
from execo_g5k import get_oar_job_nodes, OarSubmission, oargridsub, oarsub, wait_oar_job_start, get_oargrid_job_nodes, wait_oargrid_job_start, get_oargrid_job_oar_jobs, get_oar_job_kavlan, oargriddel, deploy, Deployment, wait_oar_job_start
from execo_g5k.api_utils import get_host_site,get_cluster_site, get_g5k_sites, get_g5k_clusters, get_resource_attributes, get_host_attributes, get_cluster_attributes, get_site_clusters

import logging
import time
import os
import sys
from sys import argv
from pprint import pprint
from diet_deploy import DietDeploy, getNodesfromFile
from diet_utils import get_results, get_node_name, writeNodesToFile, file_len

import matplotlib.pyplot as plt; plt.rcdefaults()
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

logger.setLevel(logging.INFO)

if len(sys.argv) > 1:
    script, oargrid_job_id = argv
    oargrid_job_id = int(oargrid_job_id)
else: 
    oargrid_job_id = -1 # -1 for a deploying with a new reservation || > 0 for working with an existing reservation


ssh_key = "/tmp/oargrid/oargrid_ssh_key_dbalouek_"+str(oargrid_job_id)
env = "http://public.lyon.grid5000.fr/~dbalouek/ens/debian/wheezy-x64-diet.dsc"
walltime = '01:00:00'
n_nodes = 1
oargridsub_opts = '-t deploy'
nodes_gr1 = "./nodes_gr1"
nodes_gr2 ="./nodes_gr2"
nodes_gr3 ="./nodes_gr3"
nodes_service = "./nodes_service"
nodefile = "./gridnodes-uniq"
try:
    os.remove(nodes_gr1); os.remove(nodes_service); os.remove(nodes_gr2); os.remove(nodes_gr3);
except OSError:
    pass

cluster = 'sagittaire'

sites = []
hosts_gr1 = {'cluster' : 'sagittaire', 'number' : n_nodes}
hosts_gr2 = {'cluster' : 'taurus', 'number' : n_nodes}
hosts_gr3 = {'cluster' : 'sagittaire', 'number' : n_nodes}

hosts_service = {'cluster' : cluster, 'number' : 2} # MA + Client

site = get_cluster_site(hosts_service["cluster"])
user_frontend_connexion_params={'user': 'dbalouek', 'default_frontend': "lyon", 'ssh_options': ('-tt', '-o', 'BatchMode=yes', '-o', 'PasswordAuthentication=no', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', '-o', 'ConnectTimeout=45')}
root_connexion_params={'user': 'root', 'ssh_options': ('-tt', '-o', 'BatchMode=yes', '-o', 'PasswordAuthentication=no', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', '-o', 'ConnectTimeout=45')}

logger.info("Job Submission...")
subs = []
sub_resources=''
for hosts in [hosts_gr1,hosts_service,hosts_gr2,hosts_gr3]:
    sub_resources += "{cluster=\\'"+hosts["cluster"]+"\\'}/nodes="+str(hosts["number"])+'+'
subs.append((OarSubmission(resources=sub_resources[:-1],walltime = walltime,additional_options = oargridsub_opts),site)) #
 
nodes = [] 

if oargrid_job_id < 0:
    job = oarsub(subs) #
    oargrid_job_id = job[0][0]
    #ssh_key = job[1]
    
    if oargrid_job_id < 0:
        print oargrid_job_id
        logger.info("No ressources availables")
        logger.info("End of program")
        sys.exit(0)
        
    logger.info("Wait for job to start...")
    print oargrid_job_id
    wait_oar_job_start(oar_job_id = oargrid_job_id)

logger.info("Wait for job to start...")
wait_oar_job_start(oargrid_job_id) #wait_oargrid_job_start(oargrid_job_id) #
print oargrid_job_id
print ssh_key 
nodes = get_oar_job_nodes(oargrid_job_id) #nodes = get_oargrid_job_nodes(oargrid_job_id)
logger.info("Job has started")
 
print nodes

logger.info("Deployment started")
#logger.setLevel(1)
nodes = deploy(Deployment(hosts = nodes, env_file = "http://public.nancy.grid5000.fr/~dbalouek/envs/debian/wheezy-x64-diet.dsc", 
                          user = "dbalouek", other_options='-d -V4'), out = True, check_deployed_command = False)
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
nb_hosts_gr1 = 0
nb_hosts_gr2 = 0
nb_hosts_gr3 = 0
nb_hosts_service = 0
for node in nodes:
    if hosts_gr1["cluster"] in node and nb_hosts_gr1 < hosts_gr1["number"]:
        logger.debug("%s / groupe1",node)
        with open(nodes_gr1, "a") as file1:
            file1.write(node)
            file1.write("\n")
            file1.close()
            nb_hosts_gr1 += 1
    elif hosts_gr2["cluster"] in node and nb_hosts_gr2 < hosts_gr2["number"]:
        logger.debug("%s / groupe2",node)
        with open(nodes_gr2, "a") as file1:
            file1.write(node)
            file1.write("\n")
            file1.close()
            nb_hosts_gr2 += 1
    elif hosts_gr3["cluster"] in node and nb_hosts_gr3 < hosts_gr3["number"]:
        logger.debug("%s / groupe3",node)
        with open(nodes_gr3, "a") as file1:
            file1.write(node)
            file1.write("\n")
            file1.close()
            nb_hosts_gr3 += 1
    elif hosts_service["cluster"] in node and nb_hosts_service < hosts_service["number"]:
        with open(nodes_service, "a") as file1:
            logger.debug("%s / service",node)
            file1.write(node)
            file1.write("\n")
            file1.close()
            nb_hosts_service += 1

if file_len(nodes_gr1) != hosts_gr1["number"] or file_len(nodes_service) != hosts_service["number"] or file_len(nodes_gr2) != hosts_gr2["number"] or file_len(nodes_gr3) != hosts_gr3["number"] :
        logger.info("The number of nodes in files mismatch the desired resources")
        logger.info("End of program")
        sys.exit(0)
        
logger.info("The number of nodes in files is matching the desired resources")

for sched in ('CONSO','NODEFLOPS'):
    params_diet = {}
    params_diet["site"] = site
    params_diet["scheduler"] = sched # CONSO | NODEFLOPS | RANDOM | CUSTOM
    params_diet["concLimit"] = "1"
    params_diet["useRate"] = "50.0"
    total_time = 0
    
    mydiet = DietDeploy(params_diet)
    mydiet.nb_nodes = n_nodes*3+2
    
    results = {}
         
    mydiet.clean_archi() #Erase files from previous deployments
     
    mydiet.create_archi_files()
            
    mydiet.retrieve_agents()
      
    mydiet.update_frontend()
         
    mydiet.update_nodes()
    
    retry = 0
    while True and retry < 5:
        
        mydiet.stop_archi()
        
        time.sleep(5)
        mydiet.start_MA()
        time.sleep(5)
        mydiet.start_servers()
        time.sleep(10)
    
    
        test_archi = mydiet.benchmark_metrics()
        if test_archi == False:
            logger.info("Some error happened! (%d tries)",retry+1)
            retry +=1
        else:
            break
    
    if retry == 5:
            logger.info("Exit! (%d tries)",retry)
            sys.exit(0)
    time.sleep(5)
     
    start,end = mydiet.start_clients()
    
    mydiet.retrieve_results(start, end)
    
    # Stats
    y_pos = []
    x_pos = []
    height = []
    servers = []
    titre = ""; titre += '[%s] Makespan = %.2f / Consumption = %.2f J / Occupation Rate = %r' % (mydiet.scheduler,mydiet.makespan,(mydiet.consumption["total"])*3600,mydiet.useRate)
    graph = ""; graph += '[%s].pdf' % (mydiet.scheduler)
    
    pp = PdfPages(graph)
    for host in mydiet.nb_tasks:
            y_pos += [ host ]
            x_pos += [ mydiet.nb_tasks[host] ]
            height += [ 0.8 ]
            servers += [ host[:-16] ]
    y_pos = np.arange(len(y_pos))
    error = 0       
             
    plt.barh(y_pos, x_pos, xerr=error, align='center', alpha=0.4)
    plt.yticks(y_pos, servers)
    plt.xlabel('Jobs')
    plt.title(titre)
    
    plt.savefig(pp, format='pdf')
    pp.close()
    #plt.show()

