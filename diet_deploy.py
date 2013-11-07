from execo import configuration, logger, Put, Process, Remote, Get, Host
#from execo.log import set_style
from diet_utils import getNodesfromFile, set_scheduler, set_parallel_jobs,\
    get_g5k_api_measures, get_nb_tasks, writeNodesToFile
from execo_g5k.api_utils import get_host_site, get_host_attributes
import sys
import os
import time

import logging
from time import gmtime, strftime

logger.setLevel(logging.DEBUG)

sched_dir = "/root/dietg/diet-sched-example/"
cfgs_dir = "/root/dietg/cfgs/"
root_connection_params = {'user': 'root', 'ssh_options': ('-tt', '-o', 'BatchMode=yes', '-o', 'PasswordAuthentication=no', '-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', '-o', 'ConnectTimeout=45')}

class DietDeploy():
    
    def __init__(self,params_diet):
        
        self.site = params_diet["site"]
        self.frontend = self.site+".grid5000.fr"
        self.user_frontend_connection_params = {'user': 'dbalouek', 'default_frontend': self.site}
        
        self.nb_nodes = 0
                  
        self.MA = [] 
        self.LA = []
        self.servers = []
        self.clients = []
        
        self.scheduler = params_diet["scheduler"]
        self.concLimit = params_diet["concLimit"]
        self.useRate = params_diet["useRate"]
        self.exp_time = params_diet["exp_time"]
        
        self.consumption = {}
        self.nb_tasks = {}
        
        self.nodes_gr1 = getNodesfromFile("./nodes_gr1")
        self.nodes_gr2 = getNodesfromFile("./nodes_gr2")
        self.nodes_gr3 = getNodesfromFile("./nodes_gr3")
        self.nodes_service = getNodesfromFile("./nodes_service")
    
        self.local_repository = os.getcwd()+"/"
        
        self.consumption_bench = {}
        self.flops_bench = {}
        self.flops_watts_bench = {}
        
        self.makespan = -1
    
    def update_frontend(self):
        logger.info("Update DIET folder on %s frontend...",self.site)
        os.system("rsync -avz --progress "+self.local_repository+"dietg/ "+self.site+".g5k:/home/dbalouek/dietg/")
        logger.info("Sent")
        
    def update_nodes(self):
        logger.info("Update DIET folder on nodes...")
        cmd = "cd /home/dbalouek/dietg/; ./update_src_directory.sh"
        a = Remote(cmd,[self.frontend],connection_params = self.user_frontend_connection_params).run()
        logger.info("Done!")
        
    def clean_archi(self):
        """ Delete all files related to an existing DIET archi """
        logger.info("Clean DIET architecture")
        process = Process("./dietg/clean_archi_diet.sh")
        process.run()
        process = Process("./dietg/clean.sh")
        process.run()
        process = Process("if [ -e ./tmp ]; then rm ./tmp; fi")
        process.run()

    def create_diet_architecture_files(self):
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
         
    def retrieve_agents(self): # A faire une seule fois!
        self.MA = getNodesfromFile("./dietg/nodes/MA.list")
        #self.LA = getNodesfromFile("./dietg/nodes/LA.list")
        self.servers += self.nodes_gr1
        self.servers += self.nodes_gr2
        self.servers += self.nodes_gr3
        
        self.clients = self.nodes_service[1]
        
    def start_MA(self):
        hostname = self.MA
        logger.info("Initialize Master Agent on node %s",hostname)
        logger.debug("Compile the executables")
        cmd = "cd "+sched_dir+"; make clean && make"
        a = Remote(cmd, hostname, connection_params = root_connection_params).run()
        for s in a.processes:
            pout = s.stdout
        logger.info(pout)
        
        logger.info("Chosen scheduler is : %s",self.scheduler)
                
        cmd = "cd /root/dietg/; ./set_masternode.sh"
        a = Remote(cmd, hostname, connection_params = root_connection_params).start()
        for s in a.processes:
            pout = s.stdout
        logger.info(pout)
        
        logger.info("Done!")
        
    def start_servers(self):
        servers = [host for host in self.servers]
        logger.info("Initialize the SeD")
        
        logger.debug("Compile the executables")
        cmd = "cd "+sched_dir+"; make clean && make"
        a = Remote(cmd, servers, connection_params = root_connection_params).run()
        for s in a.processes:
            pout = s.stdout
        logger.debug(pout)
        
        site = self.site
        cmd = "sed -i 's/LA_"+site+"/MA1/g' /root/dietg/cfgs/server.cfg;"
        a = Remote(cmd, servers, connection_params = root_connection_params).run()
        
        cmd = "cd /root/dietg/; ./set_sed.sh"
        a = Remote(cmd, servers, connection_params = root_connection_params).run()
        
        cmd = "if [ -e /root/dietg/log/total.jobs ]; then rm /root/dietg/log/total.jobs; fi"
        a = Remote(cmd, servers, connection_params = root_connection_params).run()
        
        cmd = "if [ -e /root/dietg/log/current.jobs ]; then rm /root/dietg/log/current.jobs; fi"
        a = Remote(cmd, servers, connection_params = root_connection_params).run()
        logger.info("Done!")
    
    def reload_MA(self):
        # Reinitialize tasks counters on servers
        hostname = self.MA
        cmd = "killall dietAgent; cd /root/dietg/; ./set_masternode.sh"
        a = Remote(cmd, hostname, connection_params = root_connection_params).start()
    def reload_servers(self):  
        servers = [host for host in self.servers]
        
        cmd = "if [ -e /root/MA.stat ]; then rm /root/MA.stat; touch /root/MA.stat; fi"
        a = Remote(cmd, servers, connection_params = root_connection_params).run()
        cmd = "cd /root/dietg/; ./unset_sed.sh; killall server"
        a = Remote(cmd, servers, connection_params = root_connection_params).run()
        cmd = "cd "+sched_dir+"; make"
        a = Remote(cmd, servers, connection_params = root_connection_params).run()
        cmd = "cd /root/dietg/; ./set_sed.sh"
        a = Remote(cmd, servers, connection_params = root_connection_params).run()
        
        
    def start_clients(self):
        clients = [self.clients]
        servers = [host for host in self.servers]
            
        logger.info("Initialize client on node %s",clients)
        cmd = "cd "+sched_dir+"; make clean && make"
        a = Remote(cmd, clients, connection_params = root_connection_params).run()
        for s in a.processes:
            pout = s.stdout
        logger.debug(pout)
        cmd = "cd /root/dietg/; ./set_client.sh"
        a = Remote(cmd, clients, connection_params = root_connection_params).run()
        for s in a.processes:
            pout = s.stdout
        logger.debug(pout)
        
#         logger.info("Etalonnage")
#         
#         array_process = set()
#         for serv in range(len(self.servers)):
#             cmd = "cd "+sched_dir+"; ./client_bench"
#             a = Remote(cmd, clients, connection_params = root_connection_params).start()
#             array_process.add(a)
#             logger.info("Bench started!")
#             
#         for process in array_process:
#             process.wait()
#             logger.info("Bench ended!")
#             
#         for s in array_process:
#             for a in s.processes:
#                 pout = a.stdout
#                 logger.info(pout)
#             
#         logger.info("Etalonnage termine")  
        
        cmd = "if [ -e /root/dietg/log/total.jobs ]; then rm /root/dietg/log/total.jobs; fi"
        a = Remote(cmd, servers, connection_params = root_connection_params).run()
        
        cmd = "if [ -e /root/dietg/log/current.jobs ]; then rm /root/dietg/log/current.jobs; fi"
        a = Remote(cmd, servers, connection_params = root_connection_params).run()
        
        cmd = "cd "+sched_dir+"; ./client_matrix"
        start = time.time()
        self.task_distribution(len(self.servers))
        #a = Remote(cmd, clients, connection_params = root_connection_params).run()
        end = time.time()
#         for s in a.processes:
#             pout = s.stdout
#         logger.info(pout)
        
        self.makespan = (end - start)
        
        return start,end
        
        logger.info("Done, check the logs!")
        
    def retrieve_results(self,start,end,oargrid_job_id):
        self.makespan = end - start;
        resolution = 15
        self.consumption["total"] = 0
        now = strftime("%d_%b_%H:%M", gmtime())
        
        folder_name = "results_"+str(oargrid_job_id)+"_"+self.scheduler
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        filename = "./"+folder_name+"/%s_%s.log" % (self.scheduler,str(oargrid_job_id))
        already_exists = True
        counter = 0
        while already_exists:
            try:
               with open(filename):
                   already_exists = True
                   counter += 1
                   filename = "%s_%s_%s.log" % (self.scheduler,str(oargrid_job_id),str(counter))
            except IOError:
              already_exists = False
        # Increments counter to change file name
        
        file_results = filename
        
        with open(file_results, "a") as fichier_resultats:
            fichier_resultats.write("Use Rate = %s"%(str(self.useRate)))
            fichier_resultats.write("Exp Time = %s"%(str(self.exp_time)))
            fichier_resultats.write("\n\n")            
                                     
            logger.info("Retrieve consumption per SeD")
            for sed in self.servers:
                self.consumption[sed] = get_g5k_api_measures(sed, get_host_site(sed), "pdu", start, end, resolution)
                self.consumption["total"] += float(self.consumption[sed])
                logger.info("Electric Consumption of %s = %s",sed,self.consumption[sed])
                fichier_resultats.write("Electric Consumption of %s = %sW (%sJ)"%(sed,self.consumption[sed],self.consumption[sed]*self.makespan))
                fichier_resultats.write("\n")
            
            logger.info("Retrieve consumption per MA")
            for MA in self.MA:
                self.consumption[MA] = get_g5k_api_measures(MA, get_host_site(MA), "pdu", start, end, resolution)
                self.consumption["total"] += float(self.consumption[MA])
                logger.info("Electric Consumption of %s = %s",MA,self.consumption[MA])
                fichier_resultats.write("Electric Consumption of %s = %sW (%sJ)"%(MA,self.consumption[MA],self.consumption[MA]*self.makespan))
                fichier_resultats.write("\n")
                
            logger.info("Retrieve total consumption")
            logger.info("Electric Consumption of the architecture")
            print self.consumption["total"]
            fichier_resultats.write("Total consumption = %sW (%sJ)"%(self.consumption["total"],self.consumption["total"]*self.makespan))
            fichier_resultats.write("\n")
            
            logger.info("Retrieve number of tasks per SeD")
            self.get_nb_tasks_server()
            for host,task in self.nb_tasks.iteritems():
                logger.debug("%s : %d tasks",host,task)
                fichier_resultats.write("%s : %d tasks"%(host,task))
                fichier_resultats.write("\n")
                
            logger.info("Retrieve SeD log files")
            nb_files = self.get_logs_from_server()
            logger.info("%s / %s files were retrieved",str(nb_files),str(len(self.servers)))
                        
            logger.info("Retrieve total makespan")
            logger.info("Total makespan = %d",self.makespan)
            fichier_resultats.write("Total makespan = %s"%(self.makespan))
            fichier_resultats.write("\n")
        
        fichier_resultats.close()
    
    def stop_archi(self):
        logger.info("Stop the architecture!")
        clients = [self.clients]
        servers = [host for host in self.servers]
        MA = self.MA

        cmd = "killall client > /dev/null"
        a = Remote(cmd, clients, connection_params = root_connection_params).run()
        
        cmd = "cd /root/dietg/; ./unset_sed.sh"
        a = Remote(cmd, servers, connection_params = root_connection_params).run()
        
        cmd = "cd /root/dietg/; ./unset_masternode.sh"
        a = Remote(cmd, MA, connection_params = root_connection_params).run()
        
        logger.info("Done!")
        
        for host in servers:
            os.system('ssh-keygen -f "/home/dbalouek/.ssh/known_hosts" -R '+host)
        

    def task_distribution(self,nb_nodes,pause = 10,task_action = "/root/dietg/diet-sched-example/client_matrix",hostname = None,connection_params = {'user': 'root'},capacity = 50.0,work_rate = 2):
        """ Distribute task according to:
            nb_nodes: a number of nodes
            capacity : utilization rate of the platform at a given time
            pause: time to wait between each task
            work_rate: number of tasks per working nodes
            task_action: command to execute
            hostname: client node to execute the commande"""
        
        i = 0
        j = 0
        nb_diet_error = 0
        nb_diet_success = 0
        nb_diet_nofound = 0
        distrib = []
        
        array_process = set()
        nb_initial = nb_nodes * capacity / 100
        nb_total = nb_nodes * work_rate
        if hostname is None:
            hostname = [self.clients]
        
        logger.info("Execute : "+task_action)
        #First wave
        for i in range(1,int(nb_initial)+1):
            j=i
            a = Remote(task_action, hostname, connection_params).start()
            time.sleep(1) #Dirty way to not burst the client into mistake (e.g. a server receive all rrequests at the same time)
            array_process.add(a)
            distrib.append(i)
            
        #Second wave
        for i in range(int(j+1),int(nb_total)+1):
            #Wait
            distrib.append("PAUSE")
            time.sleep(pause)
            #Action
            distrib.append(i)
            a = Remote(task_action, hostname, connection_params).start()
            array_process.add(a)
                   
        
        logger.info("Loi d'arrivee")    
        logger.info(distrib)
        for process in array_process:
            process.wait()
            for s in process.processes:
                pout = s.stdout
                logger.info(pout)
                if "no server found" in pout:
                    nb_diet_nofound += 1
                elif "diet call error" in pout:
                    nb_diet_error += 1
                elif "diet call success" in pout:
                    nb_diet_success += 1
                       
        logger.info("All the jobs are terminated (success = %s) | (error =%s)",str(nb_diet_success),str(nb_diet_error))
        
    def get_nb_tasks_server(self):
        distant_file = "/root/dietg/log/total.jobs"
        local_file = "./task_counter"
        
#         Get(self.servers, [distant_file])
        for host in self.servers:
                process = Process("scp root@"+host+":"+distant_file+" "+local_file)
                process.run()
                try: #si le fichier existe
                    with open(local_file) as fichier:
                        self.nb_tasks[host] = get_nb_tasks(local_file)
                        fichier.close
                except IOError: #si le fichier n'existe pas
                    self.nb_tasks[host] = 0
                try:
                    os.remove(local_file);
                except OSError:
                    pass
    
    def get_logs_from_server(self):
        distant_file = "/root/MA.stat"
        nb_files = 0
#         Get(self.servers, [distant_file])
        for host in self.servers:
                local_file = host+"_"+self.scheduler+"_SeD.stat"
                process = Process("scp root@"+host+":"+distant_file+" "+local_file)
                process.run()
                try: #si le fichier existe
                    with open(local_file) as fichier:
                        nb_files += 1
                        fichier.close
                except IOError: #si le fichier n'existe pas
                    pass
        return nb_files
                
    
    def benchmark_metrics(self):
        nb_diet_success = 0
        nb_diet_error = 0
        nb_diet_nofound = 0
        
        log_repository = "/root/dietg/log/"
        servers = [host for host in self.servers]
        logger.info("Clear bench files")
        
        cmd = "rm "+log_repository+"/flops_watts.bench 2> /dev/null; "+"rm "+log_repository+"/conso.bench 2> /dev/null; "+"rm "+log_repository+"/flops.bench 2> /dev/null; "
        a = Remote(cmd, servers, connection_params = root_connection_params).run()
#         for s in a.processes:
#             pout = s.stdout
#         logger.debug(pout)
#         
        # Initialise the clients
        clients = [self.clients]
        
        logger.info("Initialize client on node %s",clients)
        cmd = "cd "+sched_dir+"; make clean && make"
        a = Remote(cmd, clients, connection_params = root_connection_params).run()
        for s in a.processes:
            pout = s.stdout
        logger.info(pout)
        cmd = "cd /root/dietg/; ./set_client.sh"
        a = Remote(cmd, clients, connection_params = root_connection_params).run()
        for s in a.processes:
            pout = s.stdout
        logger.info(pout)
        
        logger.info("Benchmark_metrics")
        logger.info("Another bench just started!")
        start = time.time()
        array_process = set()
        for x in range(len(self.servers)):
            cmd = "cd "+sched_dir+"; ./client_bench"
            a = Remote(cmd, clients, connection_params = root_connection_params).start()
            time.sleep(1)
            array_process.add(a)
         
        for process in array_process:
            process.wait()
            for s in process.processes:
                pout = s.stdout
                logger.debug(pout)
                if "no server found" in pout:
                    nb_diet_nofound += 1
                elif "diet call error" in pout:
                    nb_diet_error += 1
                elif "diet call success" in pout:
                    nb_diet_success += 1
                
                
        logger.info("All the bench are terminated (success = %s) | (error =%s) | (no server found = %s)",str(nb_diet_success),str(nb_diet_error),str(nb_diet_nofound))
        end = time.time()
          
        makespan = end - start;
        if makespan < 10:
            return False
            
        logger.info("Total makespan = %d",makespan)
        resolution = 15
       
        # Electric consumption_bench metrics / CONSO     
        logger.info("Retrieve consumption_bench per SeD")
        bench_file = "conso.bench"
        for sed in self.servers:
            self.consumption_bench[sed] = get_g5k_api_measures(sed, get_host_site(sed), "pdu", start, end, resolution)
            logger.debug("Electric Consumption of %s = %sW (%sJ)",sed,self.consumption_bench[sed],self.consumption_bench[sed]*makespan)
            with open(bench_file, "w") as file1:
                file1.write(str(self.consumption_bench[sed]*makespan))
                file1.write("\n")
                file1.close()
            os.system("scp "+bench_file+" root@"+sed+":"+log_repository+" > /dev/null") #.g5k
        
        # Performance / FLOPS
        logger.info("Retrieve FLOPS per SeD")
        bench_file = "flops.bench"
        for sed in self.servers:
            self.flops_bench[sed] = get_host_attributes(sed)['performance']['node_flops'] 
            logger.debug("Flops Number of %s = %s",sed,self.flops_bench[sed])
            with open(bench_file, "w") as file1:
                file1.write(str(self.flops_bench[sed]))
                file1.write("\n")
                file1.close()
            os.system("scp "+bench_file+" root@"+sed+":"+log_repository+" > /dev/null")
        
        # Flops per Watts
        logger.info("Retrieve FLOPS/Watts per SeD")
        bench_file = "flops_watts.bench"
        for sed in self.servers:
            self.flops_watts_bench[sed] = self.flops_bench[sed] / self.consumption_bench[sed]
            logger.debug("flops_watt of %s = %s",sed,self.flops_watts_bench[sed])
            with open(bench_file, "w") as file1:
                file1.write(str(self.flops_watts_bench[sed]))
                file1.write("\n")
                file1.close()
            os.system("scp "+bench_file+" root@"+sed+":"+log_repository+" > /dev/null")
            
        logger.info("Benchmark_metrics termine")
        return True
        
        