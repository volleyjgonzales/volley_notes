#include <limits>
#include <cstdio>
#include <random>
#include <deque>
#include "structures/online_mean_variance.hpp"
using namespace volley;
template<typename T> void run(const char* name, double offset, FILE* f){
  std::mt19937_64 g(42); std::normal_distribution<double> n(0.0, 0.01);
  OnlineMeanVariance<T,100> o; std::deque<double> w;
  for(long i=1;i<=1000000;i++){ double x=offset+n(g); o.Update((T)x); w.push_back((double)(T)x); if(w.size()>100) w.pop_front();
    if(i%2000==0 && w.size()==100){ long double m=0; for(double v:w) m+=v; m/=100; long double s=0; for(double v:w) s+=(v-m)*(v-m); s/=99;
      fprintf(f,"%s,%g,%ld,%.10Lg,%.10g\n",name,offset,i,s,(double)o.GetVariance()); } }
}
int main(){ FILE* f=fopen("drift.csv","w"); fprintf(f,"type,offset,i,exact,online\n");
  run<float>("float",0.0,f); run<float>("float",1000.0,f); run<double>("double",1000.0,f); fclose(f); }
