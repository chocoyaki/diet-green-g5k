#include <iostream>
#include <cstdlib>

#include "DIET_client.h"

const char *configuration_file = "/root/dietg/cfgs/client.cfg";
const float MIN_DURATION = 20.0;
const float MAX_DURATION = 60.0;
const float FIXED_DURATION = 45.0;
const float MIN_NUMPROCESSES = 1;
const float MAX_NUMPROCESSES = 4;
const float SIZE_MATRIX = 10;

int main(int argc, char **argv) {
  srandom(time(NULL));
  double duration = FIXED_DURATION;
  int num_processes = int(random() * ((MAX_NUMPROCESSES - MIN_NUMPROCESSES) / RAND_MAX) + MIN_NUMPROCESSES);
  double *result = NULL;
  diet_profile_t *profile;
  
  diet_initialize(configuration_file, argc, argv);
  profile = diet_profile_alloc("myserv", 1, 1, 2);
  diet_scalar_set(diet_parameter(profile, 0), &duration, DIET_VOLATILE, DIET_DOUBLE);
  diet_scalar_set(diet_parameter(profile, 1), &num_processes, DIET_VOLATILE, DIET_INT);
  diet_scalar_set(diet_parameter(profile, 2), NULL, DIET_VOLATILE, DIET_DOUBLE);
  std::cout << "diet call - duration = " << duration << ", num_processes = " << num_processes << std::endl;
  if (diet_call(profile)) {
    diet_scalar_get(diet_parameter(profile, 2), &result, NULL);
    std::cout << "diet call success" << std::endl;
  } else {
    std::cout << "diet call error" << std::endl;
  }
  
  diet_profile_free(profile);
  diet_finalize();
}
