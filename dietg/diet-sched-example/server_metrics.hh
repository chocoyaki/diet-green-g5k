#ifndef _SERVER_METRICS_HH_
#define _SERVER_METRICS_HH_

#include <stdint.h>
#include <deque>
#include <vector>
#include <utility>
#include <string>
#include "boost/tuple/tuple.hpp"

typedef boost::tuple<time_t, time_t, double> measure;
typedef std::vector<measure> measures;
typedef boost::tuple<uint64_t, uint64_t, boost::tuple<measures, measures> > exec_record;
typedef std::deque<exec_record> exec_records;


// aggregate metrics of a sed execution
class MetricsAggregator {

protected:

  exec_records execs;
  std::string node_name;
  std::string cluster_name;
  std::string site_name;
  double core_flops;
  double node_flops;
  int num_cores;
  int current_jobs;
  double conso_job;

  void flush();

public:

  void init(std::string node_name = std::string(""));
  double get_core_flops();
  double get_node_flops();
  int get_num_cores();
  void record(uint64_t start, uint64_t end);
  double get_avg_pdu();
  double get_avg_cpu_idle();
  int get_current_jobs();
  double get_bench_conso();
};

#endif
