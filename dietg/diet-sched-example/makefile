.PHONY:clean

CXXOPTS=-g -O0

DIET_PREFIX ?= /usr/local

-include $(DIET_PREFIX)/include/Makefile.inc

all: client_bench client_matrix server conso.so perf.so randomize.so

client_bench: client_bench.cc
	$(CXX) $(CXXOPTS) $(DIET_CLIENT_LIBS) -Wl,-rpath=$(DIET_INSTALLDIR)/lib $(DIET_CPP_FLAGS) $^ -o $@ -ldl

client_matrix: client_matrix.cc
	$(CXX) $(CXXOPTS) $(DIET_CLIENT_LIBS) -Wl,-rpath=$(DIET_INSTALLDIR)/lib $(DIET_CPP_FLAGS) $^ -o $@ -ldl

server: server.cc server_utils.cc server_utils.hh server_metrics.cc server_metrics.hh common.hh
	$(CXX) $(CXXOPTS) $(DIET_SERVER_LIBS) -lcurl -ljsoncpp -Wl,-rpath=$(DIET_INSTALLDIR)/lib $(DIET_CPP_FLAGS) $^ -o $@

conso.so: ConsoScheduler.cc common.hh
	$(CXX) $(CXXOPTS) -shared -fPIC $(DIET_SERVER_LIBS) -Wl,-rpath=$(DIET_INSTALLDIR)/lib $(DIET_CPP_FLAGS) $^ -o $@

perf.so: PerfScheduler.cc common.hh
	$(CXX) $(CXXOPTS) -shared -fPIC $(DIET_SERVER_LIBS) -Wl,-rpath=$(DIET_INSTALLDIR)/lib $(DIET_CPP_FLAGS) $^ -o $@

randomize.so: RandomScheduler.cc common.hh
	$(CXX) $(CXXOPTS) -shared -fPIC $(DIET_SERVER_LIBS) -Wl,-rpath=$(DIET_INSTALLDIR)/lib $(DIET_CPP_FLAGS) $^ -o $@


clean:
	rm -f server *.so client_bench client_matrix
