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
#include <cstdlib>
#include <string>
#include <mutex>
#include "server.hh"

const char *configuration_file = "/root/dietg/cfgs/server.cfg";
const char *current_job_file = "/root/dietg/log/current.jobs";
const char *total_job_file = "/root/dietg/log/total.jobs";

MetricsAggregator metrics;

void start_job(){
  puts( "start_job" );
  ofstream current;
  

  my_lock();
  current.open (current_job_file);
  current << "busy\n";
  current.close();
  

  ofstream total;
  total.open (total_job_file,ofstream::app);
  //total.seekg (0, ios::end);
  total << "another task\n";
  total.close();
  
  my_unlock();

}

void end_job(){
  
  my_lock();
  puts( "end_job" );
  int number_of_lines = 0;
  string line;
  ifstream myfile(current_job_file);
    
  while (getline(myfile, line))
    {
      ++number_of_lines;
    }
  std::cout << "got number of lines = " << number_of_lines << " for file " << current_jobs << std::endl;
  myfile.close();

  
  // erase the file
  if( remove(current_job_file) != 0 )
    perror( "Error deleting jobs" );
  else
    puts( "File successfully deleted" );
  
  
    // reduce it
  ofstream current;
  current.open (current_job_file);
  int i = 0;
  while (i < number_of_lines-1){
    current << "busy\n";
  }
  current.close();
  
  my_unlock();
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
  diet_est_set_internal(estvec, EST_CONSOJOB, double(metrics.get_bench_conso()));
}

int solve_matmut(diet_profile_t *pb){
  start_job();
  std::cout << "Solve Matmut: " << std::endl;
  
  float MIN_RAND = 1.0;
  float MAX_RAND = 999.0;
  float *C = NULL;
  long i,j;   // loop index
  unsigned long k;
  int a = 0;
  size_t mA, nA, mB, nB; // size of matrix
  
  // Lecture taille matrice
  
  double * size_mat;
  diet_scalar_get(diet_parameter(pb, 0), &size_mat, NULL);
  //std::cout << "size of matrices: " << *size_mat std::endl;

  // Allocation matrice
  long row=16384*(*size_mat);
  long col=16384*(*size_mat);
  //long taille_matrice = row*col/1048576;
  /*
  C = (float*)malloc(row * col * sizeof(float));
  if (C == NULL){
    std::cout << "Allocation of memory failed for matrix " << std::endl;
    exit(0);
  }
  std::cout << "Allocation of the matrix is done! " << std::endl;

  // Intitialisation
  for (i = 0; i < (col * row); i++) {
      //std::cout << "%.0f (%.0f) / %.0f (%.0f) \n",i,log10(fabs(i)),col*row,log10(fabs(col*row)));
    C[i] = random() * ((MAX_RAND - MIN_RAND) / RAND_MAX) + MIN_RAND;
    //std::cout << "INIT : Current " << i << " Total "<< (int)(col*row) << " || Value = " <<  C[i] << std::endl;
  }
  std::cout << "Initialisation of the matrix is done! " << std::endl;

  // Calcul
  for (i=0; i< (col * row); i++){
    C[i] = C[i] * C[(col*row)-1-i];
    //std::cout << "Compute : Current " << i << " Opposite "<< (int)(col*row)-1-i << " || Value = " <<  C[i] << std::endl;
  }
  std::cout << "Computation of the matrix is done! " << std::endl;
  */

  for (k=0; k < (unsigned long)*size_mat ; k++){ //at least 9
    a = ( a + k ) % 1000;
    
  }
  std::cout << "Iterative Additions until " << k << std::endl;

  /*// Résultat attendu
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
  free(C);
  */

  /* Send the hostname as a result */
  int size_hostname = 64;
  char * hostname = (char *) malloc(64 * sizeof(char));
  //hostname[63] = '\0';
  gethostname(hostname, 63);
  //size_hostname = hostname.length();
  std::cout << "Host =  " << hostname  << std::endl;
  diet_string_set(diet_parameter(pb, 1),hostname, DIET_VOLATILE);
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
  profile_matmut = diet_profile_desc_alloc("matmut", 0, 0, 1);
  diet_generic_desc_set(diet_param_desc(profile_matmut, 0), DIET_SCALAR, DIET_DOUBLE);
  diet_generic_desc_set(diet_param_desc(profile_matmut, 1), DIET_STRING, DIET_CHAR);
  agg2 = diet_profile_desc_aggregator(profile_matmut);
  diet_aggregator_set_type(agg2, DIET_AGG_USER);
  diet_service_use_perfmetric(myperfmetric);
  
  diet_service_table_add(profile_matmut, NULL, solve_matmut);
  diet_print_service_table();


  diet_SeD(configuration_file, argc, argv);
  return 0;
}
