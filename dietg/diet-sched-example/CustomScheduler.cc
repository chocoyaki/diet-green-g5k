#include "CustomScheduler.hh"
#include <scheduler/est_internal.hh>
#include <boost/foreach.hpp>
#include <iostream>
#include "common.hh"
#include <map>

class MyScheduler : public UserScheduler {

public:

  static const char* stName;
  MyScheduler();
  ~MyScheduler();
  void init();
  static char* serialize(MyScheduler* GS);
  static MyScheduler* deserialize(const char* serializedScheduler);
  int aggregate(corba_response_t* aggrResp, size_t max_srv,
                const size_t nb_responses, const corba_response_t* responses);
};

const char* MyScheduler::stName="UserGS";

MyScheduler::~MyScheduler() {}

MyScheduler::MyScheduler() {
  this->name = this->stName;
  this->nameLength = strlen(this->name);
}

int MyScheduler::aggregate(corba_response_t* aggrResp, size_t max_srv,
                           const size_t nb_responses,
                           const corba_response_t* responses) {
  std::cout << "MyScheduler::aggregate called" << std::endl;
  
  /* Convert the corba response to a list */

  ServerList candidates = CORBA_to_STL(responses, nb_responses);
  BOOST_FOREACH(corba_server_estimation_t &e, candidates) {
    double cpu_idle = diet_est_get_internal(&(e.estim), EST_CPUIDLE, 0.0);
    double conso = diet_est_get_internal(&(e.estim), EST_CONSO, 0.0);
    double node_flops = diet_est_get_internal(&(e.estim), EST_NODEFLOPS, 0.0);
    double core_flops = diet_est_get_internal(&(e.estim), EST_COREFLOPS, 0.0);
    double num_cores = diet_est_get_internal(&(e.estim), EST_NUMCORES, 0.0);
    double last_solve = diet_est_get_internal(&(e.estim), EST_TIMESINCELASTSOLVE, 0.0);
    std::cout << "metrics for server " << e.loc.hostName << std::endl;
    std::cout << "  cpu_idle   = " << cpu_idle << std::endl;
    std::cout << "  conso      = " << conso << std::endl;
    std::cout << "  node_flops = " << node_flops << std::endl;
    std::cout << "  core_flops = " << core_flops << std::endl;
    std::cout << "  num_cores  = " << num_cores << std::endl;
    std::cout << "  last_solve  = " << last_solve << std::endl;
    std::cout << "  custom  = " << (conso / last_solve) << std::endl;

  }

  /* We select the SeD by a random sorting */
  SORT(candidates, compCustom);
  
  /* Display the sorted list*/
  int i=0;
  BOOST_FOREACH(corba_server_estimation_t &e, candidates) {
    std::cout << "Order = " << i << e.loc.hostName << std::endl;
    i++;
  }
  
  /* Convert the sorted list to a corba sequence*/
  STL_to_CORBA(candidates, aggrResp);

  
  return 0;
}

SCHEDULER_CLASS(MyScheduler)
