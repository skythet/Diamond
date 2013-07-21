# coding=utf-8

"""
The PasengerCollector collects CPU utilization of apache,nginx and passenger process
It also captures memory utilized of passenger, apache and nginx processes
Four key attributes to be published - phusion_passenger_cpu, total_apache_memory, total_passenger_mem, total_nginx_mem

To utilize this function, make sure of the following
1. Make sure to have executable of passenger-memory-stats set in os PATH
2. run diamond as root user
3. Run with command: diamond start -c /etc/diamond/diamond.conf.

PS: Don't run diamond with /etc/init.d/diamond start as it resets the os PATH to some new value
sample os PATH= /usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games:/usr/local/sbin:/usr/sbin:/sbin:/usr/lib/ruby-1.9.2-p290/bin:/usr/lib/ruby-flo/bin
/usr/lib/ruby-flo/bin is a executable for passenger-memory-stats in this case

#### Dependencies

 * passenger-memory-stats

"""
import diamond.collector
import os
import time
import re
import subprocess
from diamond.collector import str_to_bool
from cStringIO import StringIO

class PassengerCollector(diamond.collector.Collector):

    def whereis(self, program):
        for path in os.environ.get('PATH', '').split(':'):
            if os.path.exists(os.path.join(path, program)) and\
               not os.path.isdir(os.path.join(path, program)):
                return os.path.join(path, program)
        return None

    def get_default_config_help(self):
        config_help = super(PassengerCollector, self).get_default_config_help()
        config_help.update({

        })
        return config_help

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(PassengerCollector, self).get_default_config()
        config.update({
            'path':      'passenger_stats',
            })
        return config

    def collect(self):
        """
        Collector Passenger stats
        """

        location = self.whereis('passenger-memory-stats')

        if location is None:
            raise TypeError("passenger-memory-stats is not in PATH")


        def calc_cpu(processes):
            pipe1 = "top -b -n 2"
            pipe2 = "egrep " +  processes
            pipe3 = "awk {print $9}"
            p1 = subprocess.Popen(pipe1.split(), stdout=subprocess.PIPE)
            p2 = subprocess.Popen(pipe2.split(), stdin=p1.stdout, stdout=subprocess.PIPE)
            p3 = subprocess.Popen(pipe3.split(" ",1), stdin=p2.stdout, stdout=subprocess.PIPE)
            result = p3.communicate()
            cpu_usage = result[0].split('\n')[:-1]
            total_cpu = 0.0
            for index in range(len(cpu_usage)/2, len(cpu_usage)):
                cpu = float(cpu_usage[index])
                total_cpu += cpu

            return str(total_cpu)

        #k1 = "passenger-memory-stats"
        k2 = 'sed -r s/\x1B\[([0-9]{1,3}((;[0-9]{1,3})*)?)?[m|K]//g'
        q1 = subprocess.Popen(location, stdout=subprocess.PIPE)
        q2 = subprocess.Popen(k2.split(), stdin=q1.stdout, stdout=subprocess.PIPE)
        (res,err) = q2.communicate()
        f = StringIO(res)
        passenger_flag = 0
        apache_flag = 0
        nginx_flag = 0

        apache_processes = ""
        nginx_processes = ""
        passenger_processes = ""

        total_passenger_mem = 0.0
        total_apache_mem = 0.0
        total_nginx_mem = 0.0
        for line in f:
            if('Passenger processes' in line):
                passenger_flag = 1
                continue
            if('Apache processes' in line):
                apache_flag = 1
                continue
            if('Nginx processes' in line):
                nginx_flag = 1
                continue

            #If line starts with digit, then store process ids and memory
            matchObj = re.match(r"^\d", line)
            if matchObj:
                processList = line.split()
                if(apache_flag == 1):
                    apache_processes += (processList[0] + "|")
                    total_apache_mem += float(processList[4])
                if(passenger_flag == 1):
                    passenger_processes += (processList[0] + "|")
                    total_passenger_mem += float(processList[3])
                if(nginx_flag == 1):
                    nginx_processes += (processList[0] + "|")
                    total_nginx_mem += float(processList[4])

            elif('Processes:' in line):
                passenger_flag = 0
                apache_flag = 0
                nginx_flag = 0
        apache_processes = apache_processes[:-1]
        nginx_processes = nginx_processes[:-1]
        passenger_processes = passenger_processes[:-1]

        #calculate cpu of apache, nginx and passenger processes
        overall_cpu = 0
        if apache_processes:
            apache_cpu = calc_cpu(apache_processes)
            overall_cpu += float(apache_cpu)
        if nginx_processes:
            nginx_cpu = calc_cpu(nginx_processes)
            overall_cpu += float(nginx_cpu)
        if passenger_processes:
            passenger_cpu = calc_cpu(passenger_processes)
            overall_cpu += float(passenger_cpu)

        self.publish('phusion_passenger_cpu', overall_cpu)
        self.publish('total_apache_memory', total_apache_mem)
        self.publish('total_passenger_mem', total_passenger_mem)
        self.publish('total_nginx_mem', total_nginx_mem)