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

from time import gmtime, strftime

logger.setLevel(logging.INFO)

if len(sys.argv) > 1:
    script, oargrid_job_id = argv
    oargrid_job_id = int(oargrid_job_id)
else: 
    oargrid_job_id = -1 # -1 for a deploying with a new reservation || > 0 for working with an existing reservation


ssh_key = "/tmp/oargrid/oargrid_ssh_key_dbalouek_"+str(oargrid_job_id)
env = "http://public.lyon.grid5000.fr/~dbalouek/envs/debian/wheezy-x64-diet.dsc"
walltime = '02:00:00'
n_nodes = 1
oargridsub_opts = '-t deploy -t destructive'
nodes_gr1 = "./nodes_gr1"
nodes_gr2 ="./nodes_gr2"
nodes_gr3 ="./nodes_gr3"
nodes_service = "./nodes_service"
nodefile = "./gridnodes-uniq"
try:
    os.remove(nodes_gr1); os.remove(nodes_service); os.remove(nodes_gr2); os.remove(nodes_gr3);
except OSError:
    pass

cluster = 'orion'

sites = []
hosts_gr1 = {'cluster' : 'orion', 'nodes' : n_nodes, 'cores' : 12}#n_nodes}
hosts_gr2 = {'cluster' : 'sagittaire', 'nodes' : n_nodes, 'cores' : 12}
hosts_gr3 = {'cluster' : 'taurus', 'nodes' : n_nodes, 'cores' : 2}

hosts_service = {'cluster' : 'sagittaire', 'nodes' : 2} # MA + Client

site = get_cluster_site(hosts_service["cluster"])
user_frontend_connexion_params={'user': 'dbalouek', 'default_frontend': "lyon", 'ssh_options': ('-tt', '-o', 'BatchMode=yes', '-o', 'PasswordAuthentication=no', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', '-o', 'ConnectTimeout=45')}
root_connexion_params={'user': 'root', 'ssh_options': ('-tt', '-o', 'BatchMode=yes', '-o', 'PasswordAuthentication=no', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', '-o', 'ConnectTimeout=45')}

logger.info("Job Submission...")
subs = []
sub_resources=''
for hosts in [hosts_gr1,hosts_service,hosts_gr2,hosts_gr3]:
    sub_resources += "{cluster=\\'"+hosts["cluster"]+"\\'}/nodes="+str(hosts["nodes"])+'+'
subs.append((OarSubmission(resources=sub_resources[:-1],walltime = walltime,additional_options = oargridsub_opts),site)) #

total_cores = 0
for hosts in [hosts_gr1,hosts_gr2,hosts_gr3]:
    total_cores += ( hosts["nodes"]*hosts["cores"] )
print total_cores
 
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
nodes = deploy(Deployment(hosts = nodes, env_name = "wheezy-x64-diet", 
                          user = "dbalouek", other_options='-d -V4'), out = True, check_deployed_command=True)#, check_deployed_command = False)
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
    if hosts_gr1["cluster"] in node and nb_hosts_gr1 < hosts_gr1["nodes"]:
        logger.debug("%s / groupe1",node)
        with open(nodes_gr1, "a") as file1:
            file1.write(node)
            file1.write("\n")
            file1.close()
            nb_hosts_gr1 += 1
    elif hosts_gr2["cluster"] in node and nb_hosts_gr2 < hosts_gr2["nodes"]:
        logger.debug("%s / groupe2",node)
        with open(nodes_gr2, "a") as file1:
            file1.write(node)
            file1.write("\n")
            file1.close()
            nb_hosts_gr2 += 1
    elif hosts_gr3["cluster"] in node and nb_hosts_gr3 < hosts_gr3["nodes"]:
        logger.debug("%s / groupe3",node)
        with open(nodes_gr3, "a") as file1:
            file1.write(node)
            file1.write("\n")
            file1.close()
            nb_hosts_gr3 += 1
    elif hosts_service["cluster"] in node and nb_hosts_service < hosts_service["nodes"]:
        with open(nodes_service, "a") as file1:
            logger.debug("%s / service",node)
            file1.write(node)
            file1.write("\n")
            file1.close()
            nb_hosts_service += 1

if file_len(nodes_gr1) != hosts_gr1["nodes"] or file_len(nodes_service) != hosts_service["nodes"] or file_len(nodes_gr2) != hosts_gr2["nodes"] or file_len(nodes_gr3) != hosts_gr3["nodes"] :
        logger.info("The number of nodes in files mismatch the desired resources")
        logger.info("End of program")
        sys.exit(0)
        
logger.info("The number of nodes in files is matching the desired resources")

now = strftime("%d_%b_%H:%M", gmtime())

for sched in ("CONSO","PERF","RANDOMIZE"):

    params_diet = {}
    params_diet["site"] = site
    params_diet["scheduler"] = sched # CONSO | PERF | RANDOMIZE
    params_diet["concLimit"] = "1"
    params_diet["useRate"] = "50.0"
    params_diet["exp_time"] = now
    params_diet["exp_size"] = "regular" # small | regular | big
    params_diet["oargrid_job_id"] = oargrid_job_id
    params_diet["total_cores"] = total_cores
    total_time = 0
    
    mydiet = DietDeploy(params_diet)
    mydiet.nb_nodes = n_nodes*3+2
    
    results = {}
         
    mydiet.clean_archi() #Erase files from previous deployments
     
    mydiet.create_diet_architecture_files()
            
    mydiet.retrieve_agents()
      
    mydiet.update_frontend()
         
    mydiet.update_nodes()
   
    test_archi = False
    retry_max = 5
        
    while (test_archi == False):
        
        mydiet.stop_archi()
        
        
        mydiet.start_MA()
        mydiet.start_servers()
        
        test_archi = mydiet.benchmark_metrics()
                
        if (test_archi == False):
            retry_max -= 1
        if retry_max == 0:
            logger.info("Exit!")
            sys.exit()
    
    mydiet.reload_servers()

    mydiet.start,end = mydiet.start_clients()
    start,end = mydiet.start_clients()
    start,end = mydiet.start_clients()
    start,mydiet.end = mydiet.start_clients()
    
    mydiet.retrieve_results(mydiet.start, mydiet.end)
    
    time.sleep(180)
#     start,end = mydiet.start_clients()
#     mydiet.retrieve_results(start, end)
#     
    # Stats
    y_pos = []
    x_pos = []
    height = []
    servers = []
    titre = ""; titre += '[%s] Makespan = %.2f / Consumption = %.2f J / Occupation Rate = %r' % (mydiet.scheduler,mydiet.makespan,(mydiet.consumption["total"])*3600,mydiet.useRate)
    graph = ""; graph += '[%s]_%s.pdf' % (mydiet.scheduler,str(oargrid_job_id))
    
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
    
    #plt.savefig(pp, format='pdf')
    pp.close()
    #plt.show()
