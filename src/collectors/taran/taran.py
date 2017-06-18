# coding=utf-8

"""
Collect statistics from Tarantool

#### Dependencies

 * tarantool


"""
import diamond.collector
from tarantool import Connection


class TarantoolCollector(diamond.collector.Collector):

    def get_default_config_help(self):
        config_help = super(TarantoolCollector, self).get_default_config_help()
        config_help.update({
            'host': 'Tarantool host',
            'port': 'Tarantool port',
            'user': 'User',
            'password': 'Password',
        })
        return config_help

    def get_default_config(self):
        default_config = super(TarantoolCollector, self).get_default_config()
        default_config['host'] = 'localhost'
        default_config['port'] = 3301
        default_config['user'] = None
        default_config['password'] = None

        return default_config

    def collect(self):
        self.log.error("Started taran collector")
        c = Connection(
            self.config['host'],
            int(self.config['port']),
            user=self.config['user'],
            password=self.config['password']
        )
        metrics = {}

        runtime_info = c.call('box.runtime.info')[0][0]
        for item in runtime_info:
            metrics['slab.info.' + item] = runtime_info[item]

        slab_info = c.call('box.slab.info')[0][0]
        for item in slab_info:
            value = slab_info[item]
            if isinstance(slab_info[item], (str, unicode)):
                value = slab_info[item].replace('%', '')
            metrics['slab.info.' + item] = value

        stat = c.call('box.stat')[0][0]
        for item in stat:
            metrics['stat.' + item + '.rps'] = stat[item]['rps']
            metrics['stat.' + item + '.total'] = stat[item]['total']

        stat = c.call('box.stat.net')[0][0]
        for item in stat:
            metrics['stat.net.' + item + '.rps'] = stat[item]['rps']
            metrics['stat.net.' + item + '.total'] = stat[item]['total']

        self.log.info(str(metrics))
        for metric in metrics:
            self.publish(self.config['host'] + '.' + metric, float(metrics[metric]))
        return True
