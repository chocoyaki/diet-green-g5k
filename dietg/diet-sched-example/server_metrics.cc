#include <curl/curl.h>
#include <jsoncpp/json/json.h>
#include <sstream>
#include <unistd.h>
#include <iostream>
#include <boost/algorithm/string.hpp>
#include <cassert>
#include "server_metrics.hh"
#include "server_utils.hh"
#include <string>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <fstream>
#include <istream>
using namespace std;

const char *file_current_jobs = "/root/dietg/log/current.jobs";
const char *total_jobs = "/root/dietg/log/total.jobs";
const char *file_bench_conso = "/root/dietg/log/conso.bench";

// curl callback to get the data
size_t get_data_cb(void *buffer, size_t size, size_t nmemb, void *userp) {
  std::stringstream *pbuffer = reinterpret_cast<std::stringstream *>(userp);
  pbuffer->write((char*)buffer, size * nmemb);
  return size * nmemb;
}

// http get an url. returns http body + http response code
std::pair<std::string, int> get_url(std::string url) {
  std::cout << "HTTP GET " << url << std::endl;
  std::stringstream buffer;
  long http_code = 0;
  CURL *hcurl;
  hcurl = curl_easy_init();
  if(hcurl) {
    curl_easy_setopt(hcurl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(hcurl, CURLOPT_WRITEFUNCTION, get_data_cb);
    curl_easy_setopt(hcurl, CURLOPT_WRITEDATA, &buffer);
    curl_easy_setopt(hcurl, CURLOPT_SSL_VERIFYPEER, 0);
    CURLcode retcode = curl_easy_perform(hcurl);
    if(retcode != CURLE_OK)
      std::cerr << "curl_easy_perform() failed: " << curl_easy_strerror(retcode) << std::endl;
    retcode = curl_easy_getinfo(hcurl, CURLINFO_RESPONSE_CODE, &http_code);
    if(retcode != CURLE_OK)
      std::cerr << "curl_easy_getinfo() failed: " << curl_easy_strerror(retcode) << std::endl;
    curl_easy_cleanup(hcurl);
  }
  std::pair<std::string, long> result;
  result.first = buffer.str();
  result.second = http_code;
  return result;
}

// retrieve a metric from g5k api
measures get_g5k_api_measures(std::string node_name,
                              std::string site_name,
                              std::string metric,
                              uint64_t start, uint64_t end, unsigned resolution) {
  measures m = measures();
  unsigned from = utime_seconds(start);
  unsigned to = utime_seconds(end);
  if (from == to) { to ++; }
  std::cout << "get " << metric
            << " from " << format_time(from) << " (" << from
            << ") to " << format_time(to) << " (" << to << ")" << std::endl;
  std::ostringstream request;
  request << "https://api.grid5000.fr/2.1/grid5000/sites/" << site_name
          << "/metrics/" << metric
          << "/timeseries/" << node_name
          << "?resolution=" << resolution << "&from=" << from << "&to=" << to;
  std::pair<std::string, long> response = get_url(request.str());
  std::cout << response.first << std::endl;
  if (response.second / 100 == 2) {
    Json::Value root;
    Json::Reader reader;
    if (reader.parse(response.first, root)) {
      time_t ret_from = root["from"].asInt();
      time_t ret_to = root["to"].asInt();
      const Json::Value values = root["values"];
      std::cout << "got " << values.size() << " values for metric " << metric
                << " from " << format_time(ret_from) << " (" << ret_from
                << ") to " << format_time(ret_to) << " (" << ret_to << ")" << std::endl;
      int i;
      time_t slot_start_ts;
      for (i = 0, slot_start_ts = ret_from; i < values.size(); i++, slot_start_ts += resolution) {
        std::cout << "  i = " << i << " / slot_start_ts = " << slot_start_ts << " - ";
        if (! values[i].isNull()) {
          std::cout << "got " << values[i].asDouble() << std::endl;
          if (slot_start_ts >= utime_seconds(start)
              && slot_start_ts <= utime_seconds(end)
              && slot_start_ts + resolution >= utime_seconds(start)
              && slot_start_ts + resolution <= utime_seconds(end)) {
            std::cout << "    adding to measures" << std::endl;
            m.push_back(measure(slot_start_ts, slot_start_ts + resolution, values[i].asDouble()));
          }
        } else {
          std::cout << "got null value" << std::endl;
        }
      }
      assert(slot_start_ts == ret_to);
    }
  }
  return m;
}

// get the cluster of a node
std::string get_cluster(std::string node) {
  std::string cluster = pexec(std::string("python -c \"import execo_g5k; print execo_g5k.get_host_cluster('") + node + std::string("')\""));
  boost::algorithm::trim(cluster);
  return cluster;
}

// get the site of a node
std::string get_site(std::string node) {
  std::string site = pexec(std::string("python -c \"import execo_g5k; print execo_g5k.get_host_site('") + node + std::string("')\""));
  boost::algorithm::trim(site);
  return site;
}

// get a node's attribute in g5k api
Json::Value get_attr(std::string node, std::string cluster, std::string site, std::string path) {
  std::ostringstream request;
  request << "https://api.grid5000.fr/2.1/grid5000/sites/" << site
          << "/clusters/" << cluster
          << "/nodes/" << node;
  std::pair<std::string, long> response = get_url(request.str());
  if (response.second / 100 == 2) {
    Json::Value root;
    Json::Reader reader;
    if (reader.parse(response.first, root)) {
      Json::Path p(path);
      Json::Value v = p.make(root);
      return v;
    }
  }
  return Json::Value(Json::nullValue);
}

// get the total flops of a node
double get_node_flops(std::string node, std::string cluster, std::string site) {
  return get_attr(node, cluster, site, "performance.node_flops").asDouble();
}

// get the flops per core of a node
double get_core_flops(std::string node, std::string cluster, std::string site) {
  return get_attr(node, cluster, site, "performance.core_flops").asDouble();
}

// get the number of cores of a node
int get_num_cores(std::string node, std::string cluster, std::string site) {
  return get_attr(node, cluster, site, "architecture.smt_size").asInt();
}

//get the value of the consumption benchmark
double get_bench_conso(){
  double consumption = 0;
  ifstream myfile(file_bench_conso);
  myfile >> consumption;
  myfile.close();
  return consumption;
}

void MetricsAggregator::init(std::string node_name) {
  if (node_name == "") {
    const int buf_size = 256;
    char buf[buf_size];
    buf[buf_size-1] = 0;
    if (0 != gethostname(buf, buf_size-1)) {
      throw std::exception();
    }
    node_name = std::string(buf);
  }
  this->node_name = node_name;
  cluster_name = get_cluster(node_name);
  site_name = get_site(node_name);
  node_flops = ::get_node_flops(node_name, cluster_name, site_name);
  core_flops = ::get_core_flops(node_name, cluster_name, site_name);
  num_cores = ::get_num_cores(node_name, cluster_name, site_name);
  conso_job = ::get_bench_conso();
  std::cout << "node: " << node_name << std::endl;
  std::cout << "cluster: " << cluster_name << std::endl;
  std::cout << "site: " << site_name << std::endl;
  std::cout << "node_flops: " << node_flops << std::endl;
  std::cout << "core_flops: " << core_flops << std::endl;
  std::cout << "num_cores: " << num_cores << std::endl;
  std::cout << "conso_job(user_defined_benchmark): " << conso_job << std::endl;
}

double MetricsAggregator::get_core_flops() { return core_flops; }
double MetricsAggregator::get_node_flops() { return node_flops; }
int MetricsAggregator::get_num_cores() { return num_cores; }
double MetricsAggregator::get_bench_conso() { return conso_job; }

void MetricsAggregator::flush() {
  while(execs.size() > 100) {
    execs.pop_front();
  }
}

void MetricsAggregator::record(uint64_t start, uint64_t end) {
  measures consumptions = get_g5k_api_measures(node_name, site_name, "pdu", start, end, 15);
  measures loads = get_g5k_api_measures(node_name, site_name, "cpu_idle", start, end, 15);
  //int jobs = get_current_jobs();
  execs.push_back(exec_record(start, end, boost::tuple<measures, measures>(consumptions, loads)));
  flush();
}

double mean(measures v) {
  double m = 0.0;
  if (v.size() > 0) {
    double total_span = 0.0;
    for (measures::iterator i = v.begin(); i != v.end(); i++) {
      double span = i->get<1>() - i->get<0>();
      total_span += span;
      m += i->get<2>() * span;
    }
    m /= total_span;
  }
  return m;
}

double MetricsAggregator::get_avg_pdu() {
  measures all_measures;
  for (exec_records::iterator i = execs.begin(); i != execs.end(); i++) {
    all_measures.insert(all_measures.end(), i->get<2>().get<0>().begin(), i->get<2>().get<0>().end());
  }
  return mean(all_measures);
}

double MetricsAggregator::get_avg_cpu_idle() {
  measures all_measures;
  for (exec_records::iterator i = execs.begin(); i != execs.end(); i++) {
    all_measures.insert(all_measures.end(), i->get<2>().get<1>().begin(), i->get<2>().get<1>().end());
  }
  return mean(all_measures);
}

// get the number of current job
int MetricsAggregator::get_current_jobs(){
  int number_of_lines = 0;
  string line;
  ifstream myfile(file_current_jobs);
    
  while (getline(myfile, line))
    {
      number_of_lines += 1;
    }
  std::cout << "got number of lines = " << number_of_lines << " for file " << file_current_jobs << std::endl;
  myfile.close();
  return number_of_lines;
}
