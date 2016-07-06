# Copyright 2016 Twitter. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import heron.explorer.src.python.args as args
import heron.explorer.src.python.utils as utils
import sys
from heron.common.src.python.color import Log
from tabulate import tabulate


def create_parser(subparsers):
  spouts_parser = subparsers.add_parser(
    'spouts-metric',
    help='Display info of a topology\'s spouts metrics',
    usage="%(prog)s cluster/[role]/[env] topology-name [options]",
    add_help=False)
  args.add_cluster_role_env(spouts_parser)
  args.add_topology_name(spouts_parser)
  args.add_verbose(spouts_parser)
  args.add_tracker_url(spouts_parser)
  args.add_config(spouts_parser)
  args.add_spout_name(spouts_parser)
  spouts_parser.set_defaults(subcommand='spouts-metric')

  bolts_parser = subparsers.add_parser(
   'bolts-metric',
    help='Display info of a topology\'s bolts metrics',
    usage="%(prog)s cluster/[role]/[env] topology-name [options]",
    add_help=False)
  args.add_cluster_role_env(bolts_parser)
  args.add_topology_name(bolts_parser)
  args.add_verbose(bolts_parser)
  args.add_tracker_url(bolts_parser)
  args.add_config(bolts_parser)
  args.add_bolt_name(bolts_parser)
  bolts_parser.set_defaults(subcommand='bolts-metric')

  containers_parser = subparsers.add_parser(
    'containers',
    help='Display info of a topology\'s containers metrics',
    usage="%(prog)s cluster/[role]/[env] topology-name [options]",
    add_help=False)
  args.add_cluster_role_env(containers_parser)
  args.add_topology_name(containers_parser)
  args.add_verbose(containers_parser)
  args.add_tracker_url(containers_parser)
  args.add_config(containers_parser)
  args.add_container_id(containers_parser)
  containers_parser.set_defaults(subcommand='containers')
  return subparsers


def parse_topo_loc(cl_args):
  try:
    topo_loc = cl_args['cluster/[role]/[env]'].split('/')
    topo_name = cl_args['topology-name']
    topo_loc.append(topo_name)
    if len(topo_loc) != 4:
      raise
    return topo_loc
  except Exception:
    Log.error('Invalid topology location')
    raise


def to_table(metrics):
  all_queries = utils.metric_queries()
  m = utils.queries_map()
  names = metrics.values()[0].keys()
  stats = []
  for n in names:
    info = [n]
    for field in all_queries:
      try:
        info.append(str(metrics[field][n]))
      except KeyError:
        pass
    stats.append(info)
  header = ['container id'] + [m[k] for k in all_queries if k in metrics.keys()]
  return stats, header


def run_spouts(command, parser, cl_args, unknown_args):
  cluster, role, env = cl_args['cluster'], cl_args['role'], cl_args['environ']
  topology = cl_args['topology-name']
  try:
    result = utils.get_topology_info(cluster, env, topology, role)
    spouts = result['physical_plan']['spouts'].keys()
    spout_name = cl_args['spout']
    if spout_name:
      if spout_name in spouts:
        spouts = [spout_name]
      else:
        Log.error('Unknown spout: \'%s\'' % spout_name)
        raise
  except Exception:
    return False
  spouts_result = []
  for spout in spouts:
    try:
      metrics = utils.get_component_metrics(spout, cluster, env, topology, role)
      stat, header = to_table(metrics)
      spouts_result.append((spout, stat, header))
    except:
      return False
  for spout, stat, header in spouts_result:
    print('\'%s\' metrics:' % spout)
    print(tabulate(stat, headers=header))
  return True


def run_bolts(command, parser, cl_args, unknown_args):
  cluster, role, env = cl_args['cluster'], cl_args['role'], cl_args['environ']
  topology = cl_args['topology-name']
  try:
    result = utils.get_topology_info(cluster, env, topology, role)
    bolts = result['physical_plan']['bolts'].keys()
    bolt_name = cl_args['bolt']
    if bolt_name:
      if bolt_name in bolts:
        bolts = [bolt_name]
      else:
        Log.error('Unknown bolt: \'%s\'' % bolt_name)
        raise
  except Exception:
    return False
  bolts_result = []
  for bolt in bolts:
    try:
      metrics = utils.get_component_metrics(bolt, cluster, env, topology, role)
      stat, header = to_table(metrics)
      bolts_result.append((bolt, stat, header))
    except Exception:
      return False
  for bolt, stat, header in bolts_result:
    print('\'%s\' metrics:' % bolt)
    print(tabulate(stat, headers=header))
  return True


def run_containers(command, parser, cl_args, unknown_args):
  cluster, role, env = cl_args['cluster'], cl_args['role'], cl_args['environ']
  topology = cl_args['topology-name']
  container_id = cl_args['cid']
  result = utils.get_topology_info(cluster, env, topology, role)
  containers = result['physical_plan']['stmgrs']
  all_bolts, all_spouts = set(), set()
  for container, bolts in result['physical_plan']['bolts'].items():
    all_bolts = all_bolts | set(bolts)
  for container, spouts in result['physical_plan']['spouts'].items():
    all_spouts = all_spouts | set(spouts)
  stmgrs = containers.keys()
  stmgrs.sort()
  if container_id is not None:
    try:
      stmgrs = [stmgrs[container_id]]
    except:
      Log.error('Invalid container id: %d' % container_id)
      return False
  table = []
  for id, name in enumerate(stmgrs):
    cid = id + 1
    host = containers[name]["host"]
    port = containers[name]["port"]
    pid = containers[name]["pid"]
    instances = containers[name]["instance_ids"]
    bolt_nums = len([instance for instance in instances if instance in all_bolts])
    spout_nums = len([instance for instance in instances if instance in all_spouts])
    table.append([cid, host, port, pid, bolt_nums, spout_nums, len(instances)])
  headers = ["container", "host", "port", "pid", "#bolt", "#spout", "#instance"]
  sys.stdout.flush()
  print(tabulate(table, headers=headers))
  return True
