// Filename: server.hh
// Description: 
// Author: Daniel Balouek
// Maintainer: 
// Created: lun. nov. 11 20:32:22 2013 (+0100)
// Version: 
// Last-Updated: 
//           By: 
//     Update #: 0
// URL: 

// 
// server.hh ends here

const char *lockfile ="/root/dietg/log/lockfile.lock";

inline bool exists_test (const std::string& name) {
    ifstream f(name.c_str());
    if (f.good()) {
        f.close();
        return true;
    } else {
        f.close();
        return false;
    }   
}

void my_lock(){
  while (exists_test(lockfile) == true)
    sleep(1);
  ofstream lock;
  lock.open(lockfile);
  lock << "lock!\n";
  lock.close();
}

void my_unlock(){
  remove(lockfile);
}
