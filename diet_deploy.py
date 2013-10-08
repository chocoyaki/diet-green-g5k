from execo import configuration, logger, Put, Process, Remote, Get, Host
from execo.log import set_style
from diet_utils import getNodesfromFile, set_scheduler, set_parallel_jobs,\
    get_g5k_api_measures, get_nb_tasks, writeNodesToFile
from execo_g5k.api_utils import get_host_site
import sys
import os
import time

import logging
import os
import time

logger.setLevel(logging.DEBUG)

sched_dir = "/root/dietg/diet-sched-example/"
cfgs_dir = "/root/dietg/cfgs/"
root_connexion_params = {'user': 'root', 'ssh_options': ('-tt', '-o', 'BatchMode=yes', '-o', 'PasswordAuthentication=no', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', '-o', 'ConnectTimeout=45')}

class DietDeploy():
    
    def __init__(self,params_diet):
        
        self.site = params_diet["site"]
        self.frontend = self.site+".grid5000.fr"
        self.user_frontend_connexion_params = {'user': 'dbalouek', 'default_frontend': self.site}
        
                      
        self.MA = [] 
        self.LA = []
        self.servers = []
        self.clients = []
        
        self.scheduler = params_diet["scheduler"]
        self.concLimit = params_diet["concLimit"]
        self.useRate = params_diet["useRate"]
        
        self.consumption = {}
        self.nb_tasks = {}
        
        self.nodes_perf = getNodesfromFile("./nodes_perf")
        self.nodes_green = getNodesfromFile("./nodes_green")
        self.nodes_service = getNodesfromFile("./nodes_service")
    
        self.local_repository = os.getcwd()+"/"
        
        
        self.makespan = -1
    
    def update_frontend(self):
        logger.info("Update DIET folder on %s frontend...",self.site)
        os.system("rsync -avz "+self.local_repository+"dietg "+self.site+".g5k:/home/dbalouek/")
        logger.info("Sent")
        
    def update_nodes(self):
        logger.info("Update DIET folder on nodes...")
        cmd = "cd /home/dbalouek/dietg/; ./update_src_directory.sh"
        a = Remote(cmd,[self.frontend],connexion_params = self.user_frontend_connexion_params).run()
        logger.info("Done!")
        
    def clean_archi(self):
        """ Delete all files related to an existing DIET archi """
        logger.info("Clean DIET architecture")
        process = Process("./dietg/clean_archi_diet.sh")
        process.run()
        process = Process("./dietg/clean.sh")
        process.run()
        process = Process("rm ./tmp")
        process.run()
            
    def create_archi_files(self):
        logger.info("Create a DIET architecture") 
        # Architecture without LA
        process = Process("./dietg/set_archi_diet_4.sh gridnodes "+str(self.nodes_service[0]))
        process.run()
        
        MA_file = "./dietg/cfgs/MA1.cfg"
        SeD_file = ['./dietg/cfgs/server.cfg']
        logger.info("Create MA file")
        set_scheduler(MA_file, self.scheduler)
        logger.info("Create Sed files")
        for file2 in SeD_file:
            # print file2
            set_parallel_jobs(file2, self.concLimit)
         
    def retrieve_agents(self):
        self.MA = getNodesfromFile("./dietg/nodes/MA.list")
        #self.LA = getNodesfromFile("./dietg/nodes/LA.list")
        self.servers += self.nodes_perf
        self.servers += self.nodes_green
        
        self.clients = self.nodes_service[1]
        
    def start_MA(self):
        hostname = self.MA
        logger.info("Initialize Master Agent on node %s",hostname)
        logger.debug("Compile the executables")
        cmd = "cd "+sched_dir+"; make clean && make"
        a = Remote(cmd, hostname, connexion_params = root_connexion_params).run()
        for s in a.processes():
            pout = s.stdout()
        logger.info(pout)
        
        logger.info("Chosen scheduler is : %s",self.scheduler)
                
        cmd = "cd /root/dietg/; ./set_masternode.sh"
        a = Remote(cmd, hostname, connexion_params = root_connexion_params).run()
        for s in a.processes():
            pout = s.stdout()
        logger.info(pout)
        
        logger.info("Done!")
        
    def start_servers(self):
        servers = [host for host in self.servers]
        logger.info("Initialize the SeD")
        
        logger.debug("Compile the executables")
        cmd = "cd "+sched_dir+"; make clean && make"
        a = Remote(cmd, servers, connexion_params = root_connexion_params).run()
        for s in a.processes():
            pout = s.stdout()
        logger.debug(pout)
        
        site = self.site
        cmd = "sed -i 's/LA_"+site+"/MA1/g' /root/dietg/cfgs/server.cfg;"
        a = Remote(cmd, servers, connexion_params = root_connexion_params).run()
        
        cmd = "cd /root/dietg/; ./set_sed.sh"
        a = Remote(cmd, servers, connexion_params = root_connexion_params).run()
        
        logger.info("Done!")
        
    def start_clients(self):
        clients = [self.clients]
            
        logger.info("Initialize client on node %s",clients)
        cmd = "cd "+sched_dir+"; make clean && make"
        a = Remote(cmd, clients, connexion_params = root_connexion_params).run()
        for s in a.processes():
            pout = s.stdout()
        logger.debug(pout)
        cmd = "cd /root/dietg/; ./set_client.sh"
        a = Remote(cmd, clients, connexion_params = root_connexion_params).run()
        for s in a.processes():
            pout = s.stdout()
        logger.debug(pout)
        
        logger.info("Etalonnage")
        
        array_process = set()
        for serv in range(len(self.servers)):
            cmd = "cd "+sched_dir+"; ./client_bench"
            a = Remote(cmd, clients, connexion_params = root_connexion_params).start()
            array_process.add(a)
            
        for process in array_process:
            process.wait()
        logger.info("Etalonnage termine")  
            
        
        for s in a.processes():
            pout = s.stdout()
        logger.info(pout)
        
        cmd = "cd "+sched_dir+"; ./client_matrix"
        start = time.time()
        self.task_distribution(len(self.servers))
        #a = Remote(cmd, clients, connexion_params = root_connexion_params).run()
        end = time.time()
#         for s in a.processes():
#             pout = s.stdout()
#         logger.info(pout)
        
        self.makespan = (end - start)
        
        return start,end
        
        logger.info("Done, check the logs!")
        
    def retrieve_results(self,start,end):
        resolution = 15
        self.consumption["total"] = 0
        
        
        logger.info("Retrieve consumption per SeD")
        for sed in self.servers:
            self.consumption[sed] = get_g5k_api_measures(sed, get_host_site(sed), "pdu", start, end, resolution)
            self.consumption["total"] += float(self.consumption[sed])
            logger.info("Electric Consumption of %s = %s",sed,self.consumption[sed])
        
        logger.info("Retrieve consumption per MA")
        for MA in self.MA:
            self.consumption[MA] = get_g5k_api_measures(MA, get_host_site(MA), "pdu", start, end, resolution)
            self.consumption["total"] += float(self.consumption[MA])
            logger.info("Electric Consumption of %s = %s",MA,self.consumption[MA])
            
        logger.info("Retrieve total consumption")
        logger.debug("Electric Consumption of the architecture")
        print self.consumption["total"]
        
        logger.info("Retrieve number of tasks per SeD")
        self.get_nb_tasks_server()
                    
        logger.info("Retrieve total makespan")
        self.makespan = end - start;
        logger.info("Total makespan = %d",self.makespan)
        
    
    def stop_archi(self):
        logger.info("Stop the architecture!")
        clients = [self.clients]
        servers = [host for host in self.servers]
        MA = self.MA

        cmd = "killall client"
        a = Remote(cmd, clients, connexion_params = root_connexion_params).run()
        
        cmd = "cd /root/dietg/; ./unset_sed.sh"
        a = Remote(cmd, servers, connexion_params = root_connexion_params).run()
        
        cmd = "cd /root/dietg/; ./unset_masternode.sh"
        a = Remote(cmd, MA, connexion_params = root_connexion_params).run()
        
        logger.info("Done!")
        

    def task_distribution(self,nb_nodes,pause = 20,task_action = "/root/dietg/diet-sched-example/client_matrix",hostname = None,connexion_params = {'user': 'root'},capacity = 50.0,work_rate = 2):
        """ Distribute task according to:
            nb_nodes: a number of nodes
            capacity : utilization rate of the platform at a given time
            pause: time to wait between each task
            work_rate: number of tasks per working nodes
            task_action: command to execute
            hostname: client node to execute the commande"""
        
        i = 0
        j = 0
        distrib = []
        
        array_process = set()
        nb_initial = nb_nodes * capacity / 100
        nb_total = nb_nodes * work_rate
        if hostname is None:
            hostname = [self.clients]
        
        #First wave
        for i in range(1,int(nb_initial)+1):
            j=i
            a = Remote(task_action, hostname, connexion_params).start()
            array_process.add(a)
            distrib.append(i)
            logger.debug("Execute : "+task_action)
            
        #Second wave
        for i in range(int(j+1),int(nb_total)+1):
            #Wait
            logger.debug("PAUSE")
            distrib.append("PAUSE")
            time.sleep(pause)
            #Action
            distrib.append(i)
            a = Remote(task_action, hostname, connexion_params).start()
            array_process.add(a)
            logger.debug(task_action)
        
        
        
        logger.info("Loi d'arrivee")    
        logger.info(distrib)
        for process in array_process:
            process.wait()
        logger.info("All the jobs are terminated")
        
    def get_nb_tasks_server(self):
        distant_file = "/root/dietg/log/total.jobs"
        local_file = "./task_counter"
        for host in self.servers:
            process = Process("scp root@"+host+":"+distant_file+" "+local_file)
            process.run()
            self.nb_tasks[host] = get_nb_tasks(local_file)
        try:
            os.remove(local_file);
        except OSError:
            pass
        
        