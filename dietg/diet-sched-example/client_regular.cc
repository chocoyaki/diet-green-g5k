#include <iostream>
#include <cstdlib>
#include <time.h>


#include "DIET_client.h"

const char *configuration_file = "/root/dietg/cfgs/client.cfg";
const float MIN_DURATION = 20.0;
const float MAX_DURATION = 60.0;
const float MIN_NUMPROCESSES = 1;
const float MAX_NUMPROCESSES = 4;
const double SIZE_MATRIX = 1e10; //at least 09

int main(int argc, char **argv) {
  srandom(time(NULL));
  //double duration = random() * ((MAX_DURATION - MIN_DURATION) / RAND_MAX) + MIN_DURATION;
  
  double size_matrix = SIZE_MATRIX;
  double size_hostname;
  char * hostname[64];
  int num_processes = int(random() * ((MAX_NUMPROCESSES - MIN_NUMPROCESSES) / RAND_MAX) + MIN_NUMPROCESSES);
  double *result = NULL;
  diet_profile_t *profile;
  time_t start,stop;
  double elapsed_secs_time;

  /* Matrix multiplication */
  
  time(&start);
    
  diet_initialize(configuration_file, argc, argv);
  
  profile=diet_profile_alloc("matmut",0,0,1);
  diet_scalar_set(diet_parameter(profile, 0), &size_matrix, DIET_VOLATILE, DIET_DOUBLE);
  diet_string_set(diet_parameter(profile, 1), NULL, DIET_VOLATILE);
  if (!diet_call(profile)) {
    std::cout << "diet call success" << std::endl;
    diet_string_get(diet_parameter(profile,1), &hostname, NULL);
    time(&stop);
    elapsed_secs_time = difftime(stop,start); 
    std::cout << *hostname << " : Time for client (regular) = " << elapsed_secs_time << std::endl;
  } 
  else {
    std::cout << "diet call error" << std::endl;
  }
  
  diet_profile_free(profile);
  diet_finalize();
}
