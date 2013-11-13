// Filename: server.hh
// Description: 
// Author: Daniel Balouek

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

using namespace std;

const char *lockfile ="/root/dietg/log/lockfile.lock";

inline bool exists_test (const char* name) {
  ifstream f(name);
  if (f.good()) {
    f.close();
    return true;
  } 
  else {
    f.close();
    return false;
  }   
}

void my_lock(){
  while (exists_test(lockfile) == true){
    sleep(1);
  }
  ofstream lock;
  lock.open(lockfile);
  lock << "lock!\n";
  lock.close();
}

void my_unlock(){
  remove(lockfile);
}
