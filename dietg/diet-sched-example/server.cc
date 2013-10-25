#include <iostream>
#include "common.hh"
#include "server_metrics.hh"
#include "server_utils.hh"
#include "DIET_server.h"
#include "scheduler/est_internal.hh"
#include <fstream>
#include <cmath>
#include <stdio.h>
#include <iostream>
#include <fstream>
#include <istream>
using namespace std;

const char *configuration_file = "/root/dietg/cfgs/server.cfg";
const char *current_job_file = "/root/dietg/log/current.jobs";
const char *total_job_file = "/root/dietg/log/total.jobs";

MetricsAggregator metrics;

void start_job(){
  puts( "start_job" );
  ofstream current;
  current.open (current_job_file);
  current << "busy\n";
  current.close();

  ofstream total;
  total.open (total_job_file,ofstream::app);
  //total.seekg (0, ios::end);
  total << "another task\n";
  total.close();  
}

void end_job(){
  puts( "end_job" );
  if( remove(current_job_file) != 0 )
    perror( "Error deleting jobs" );
  else
    puts( "File successfully deleted" );
}

int handler_myserv(diet_profile_t *p) {
  start_job();
  uint64_t start_t = utime();
  double *duration;
  int *num_processes;
  double *result;
  diet_scalar_get(diet_parameter(p, 0), &duration, NULL);
  diet_scalar_get(diet_parameter(p, 1), &num_processes, NULL);
  diet_scalar_get(diet_parameter(p, 2), &result, NULL);
  std::cout << "in: " << *duration << ", " << *num_processes << std::endl;
  stress(*duration, *num_processes);
  *result = 0.0;
  metrics.record(start_t, utime());
  end_job();
  return 1;
}

void myperfmetric(diet_profile_t *profile, estVector_t estvec) {
  diet_est_set_internal(estvec, EST_CPUIDLE, metrics.get_avg_cpu_idle());
  diet_est_set_internal(estvec, EST_CONSO, metrics.get_avg_pdu());
  diet_est_set_internal(estvec, EST_NODEFLOPS, metrics.get_node_flops());
  diet_est_set_internal(estvec, EST_COREFLOPS, metrics.get_core_flops());
  diet_est_set_internal(estvec, EST_NUMCORES, double(metrics.get_num_cores()));
  diet_est_set_internal(estvec, EST_CURRENTJOBS, double(metrics.get_current_jobs()));
}

int solve_matmut(diet_profile_t *pb){
  start_job();
  std::cout << "Solve Matmut: " << std::endl;
  double *A = NULL;
  double *B = NULL;
  double *C = NULL;
  long i,j;   // loop index
  size_t mA, nA, mB, nB; // size of matrix
  
  // Lecture taille matrice
  
  double * size_mat;
  diet_scalar_get(diet_parameter(pb, 0), &size_mat, NULL);
  //std::cout << "size of matrices: " << *size_mat std::endl;

  // Allocation matrice
  long row=1024*sqrt(*size_mat);
  long col=1024*sqrt(*size_mat);
  long taille_matrice = row*col/1048576;
  
  A = (double*)malloc(row * col * sizeof(double));
  if (A == NULL){
    std::cout << "Allocation of memory failed for matrix " << std::endl;
    exit(0);
  }
  B = (double*)malloc(row * col * sizeof(double));
  if (B == NULL){
    std::cout << "Allocation of memory failed for matrix " << std::endl;
    exit(0);
  }
  C = (double*)malloc(row * col * sizeof(double));
  if (C == NULL){
    std::cout << "Allocation of memory failed for matrix " << std::endl;
    exit(0);
  }
  // Intitialisation
  for (i = 0; i < (col * row); i++) {
      //std::cout << "%.0f (%.0f) / %.0f (%.0f) \n",i,log10(fabs(i)),col*row,log10(fabs(col*row)));
      A[(int)i] = 2;
      B[(int)i] = 4;
  }
  // Calcul
  for (i=0; i<col*row; i++){
    C[i]=A[i]*B[i];
  }
  // Résultat attendu
  bool check = true;
  for (i=0; i<col*row; i++){
    if (C[i] != A[i] * B[i]){
      check = false;
    }
  }
  if (check == true)
    std::cout << "Multiplication succeed on " << col*row  << " items" << std::endl;
  else
    std::cout << "Multiplication failed " << std::endl;
  free(A);
  free(B);
  free(C);
  end_job();
  return 0;
}

int main(int argc, char **argv) {

  metrics.init(argc > 1 ? argv[1] : "");
  
  if( remove(total_job_file) != 0 )
    perror( "Error deleting total job file" );
  else
    puts( "Total job file successfully deleted" );
  
  if( remove(current_job_file) != 0 )
    perror( "Error deleting current job file" );
  else
    puts( "Current job file successfully deleted" );
  
  diet_profile_desc_t *profile;
  diet_profile_desc_t *profile_matmut;
  diet_aggregator_desc_t *agg;
  diet_aggregator_desc_t *agg2;

  diet_service_table_init(1);
  profile = diet_profile_desc_alloc("myserv", 1, 1, 2);
  diet_generic_desc_set(diet_param_desc(profile, 0), DIET_SCALAR, DIET_DOUBLE);
  diet_generic_desc_set(diet_param_desc(profile, 1), DIET_SCALAR, DIET_INT);
  diet_generic_desc_set(diet_param_desc(profile, 2), DIET_SCALAR, DIET_DOUBLE);
  agg = diet_profile_desc_aggregator(profile);
  diet_aggregator_set_type(agg, DIET_AGG_USER);
  diet_service_use_perfmetric(myperfmetric);
  
  /* for this service, use a developper defined scheduler */
  
  //diet_aggregator_set_type(agg, DIET_AGG_PRIORITY);
  // diet_aggregator_priority_min(agg, EST_CONSO);
  //  diet_aggregator_priority_max(agg, EST_TIMESINCELASTSOLVE);
    
  diet_service_table_add(profile, NULL, handler_myserv);
  diet_profile_desc_free(profile);

  /* Matrix multiplication */
  profile_matmut = diet_profile_desc_alloc("matmut", 0, 0, 0);
  diet_generic_desc_set(diet_param_desc(profile_matmut, 0), DIET_SCALAR, DIET_DOUBLE);
  agg2 = diet_profile_desc_aggregator(profile_matmut);
  diet_aggregator_set_type(agg2, DIET_AGG_USER);
  diet_service_use_perfmetric(myperfmetric);
  
  diet_service_table_add(profile_matmut, NULL, solve_matmut);
  diet_print_service_table();


  diet_SeD(configuration_file, argc, argv);
  return 0;
}
