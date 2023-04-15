import socket
from sqlalchemy.orm import Load
from babel.dates import format_timedelta as babel_format_timedelta

from flask_babelex import gettext as __
from flask_babelex import lazy_gettext as _
import urllib
from hiddifypanel.models import *
from hiddifypanel.panel.database import db
import datetime
from flask import jsonify, g, url_for, Markup
from wtforms.validators import ValidationError
from flask import flash as flask_flash
to_gig_d = 1000*1000*1000


def add_or_update_proxy(commit=True,child_id=0,**proxy):
    dbproxy = Proxy.query.filter(
        Proxy.name == proxy['name']).first()
    if not dbproxy:
        dbproxy = Proxy()
        db.session.add(dbproxy)
    dbproxy.enable = proxy['enable']
    dbproxy.name = proxy['name']
    dbproxy.proto = proxy['proto']
    dbproxy.transport = proxy['transport']
    dbproxy.cdn = proxy['cdn']
    dbproxy.l3 = proxy['l3']
    dbproxy.child_id = child_id
    if commit:
        db.session.commit()
def add_or_update_domain(commit=True,child_id=0,**domain):
    dbdomain = Domain.query.filter(
        Domain.domain == domain['domain']).first()
    if not dbdomain:
        dbdomain = Domain(domain=domain['domain'])
        db.session.add(dbdomain)
    dbdomain.child_id = child_id

    dbdomain.mode = domain['mode']
    dbdomain.cdn_ip = domain.get('cdn_ip', '')
    dbdomain.alias = domain.get('alias', '')
    show_domains = domain.get('show_domains', [])
    dbdomain.show_domains = Domain.query.filter(
        Domain.domain.in_(show_domains)).all()
    if commit:
        db.session.commit()

def add_or_update_user1(commit=True,**user):
    dbuser = User.query.filter(User.uuid == user['uuid']).first()

    if not dbuser:
        dbuser = User()
        dbuser.uuid = user['uuid']
        db.session.add(dbuser)
    
    if user.get('expiry_time',''):
        if user.get('last_reset_time',''):
            last_reset_time = datetime.datetime.strptime(user['last_reset_time'], '%Y-%m-%d')
        else:
            last_reset_time = datetime.date.today()

        expiry_time = datetime.datetime.strptime(user['expiry_time'], '%Y-%m-%d')
        dbuser.start_date=    last_reset_time
        dbuser.package_days=(expiry_time-last_reset_time).days

    elif 'package_days' in user:
        dbuser.package_days=user['package_days']
        if user.get('start_date',''):
            dbuser.start_date=datetime.datetime.strptime(user['start_date'], '%Y-%m-%d')
        else:
            dbuser.start_date=None
    dbuser.current_usage_GB = user['current_usage_GB']
    
    dbuser.usage_limit_GB = user['usage_limit_GB']
    dbuser.name = user['name']
    dbuser.comment = user.get('comment', '')
    dbuser.mode = user.get('mode', user.get('monthly', 'false') == 'true')
    # dbuser.last_online=user.get('last_online','')
    if commit:
        db.session.commit()


def bulk_register_parent_domains(parent_domains,commit=True,remove=False):
    for p in parent_domains:
        add_or_update_parent_domains(commit=False,**p)
    if remove:
        dd = {p.domain: 1 for p in parent_domains}
        for d in ParentDomain.query.all():
            if d.domain not in dd:
                db.session.delete(d)
    if commit:
        db.session.commit()

def bulk_register_domains(domains,commit=True,remove=False,override_child_id=None):
    child_ids={}
    for domain in domains:
        child_id=override_child_id if override_child_id is not None else get_child(domain.get('child_unique_id',None))
        child_ids[child_id]=1
        add_or_update_domain(commit=False,child_id=child_id,**domain)
    if remove and len(child_ids):
        dd = {d['domain']: 1 for d in domains}
        for d in Domain.query.filter(Domain.child_id.in_(child_ids)):
            if d.domain not in dd:
                db.session.delete(d)
    if commit:
        db.session.commit()
def bulk_register_users(users=[],commit=True,remove=False):
    for u in users:
        add_or_update_user(commit=False,**u)
    if remove:
        dd = {u.uuid: 1 for u in users}
        for d in User.query.all():
            if d.uuid not in dd:
                db.session.delete(d)
    if commit:
        db.session.commit()
def bulk_register_configs(hconfigs,commit=True,override_child_id=None,override_unique_id=True):
    print(hconfigs)
    for conf in hconfigs:
        # print(conf)
        if conf['key']==ConfigEnum.unique_id and not override_unique_id:
            continue
        child_id=override_child_id if override_child_id is not None else get_child(conf.get('child_unique_id',None))
        # print(conf)
        add_or_update_config(commit=False,child_id=child_id,**conf)
    if commit:
        db.session.commit()

def bulk_register_proxies(proxies,commit=True,override_child_id=None):
    for proxy in proxies:
        child_id=override_child_id if override_child_id is not None else get_child(proxy.get('child_unique_id',None))
        add_or_update_proxy(commit=False,child_id=child_id,**proxy)

    
def set_db_from_json(json_data, override_child_id=None, set_users=True, set_domains=True, set_proxies=True, set_settings=True, remove_domains=False, remove_users=False, override_unique_id=True):
    new_rows = []
    if set_users and 'users' in json_data:
        bulk_register_users(json_data['users'],commit=False,remove=remove_users)
    if set_domains and 'domains' in json_data:
        bulk_register_domains(json_data['domains'],commit=False,remove=remove_domains,override_child_id=override_child_id)
    if set_domains and 'parent_domains' in json_data:
        bulk_register_parent_domains(json_data['parent_domains'],commit=False,remove=remove_domains)
    if set_settings and 'hconfigs' in json_data:
        bulk_register_configs(json_data["hconfigs"],commit=False,override_child_id=override_child_id,override_unique_id=override_unique_id)
        if 'proxies' in json_data:
            bulk_register_proxies(json_data['proxies'],commit=False,override_child_id=override_child_id)
    db.session.commit()




def get_random_string(min_=10,max_=30):
    # With combination of lower and upper case
    import string
    import random
    length=random.randint(min_, max_)
    characters = string.ascii_letters + string.digits
    result_str = ''.join(random.choice(characters) for i in range(length))
    return result_str




def get_user_link(uuid, domain, mode='',username=''):
    is_cdn= domain.mode == DomainType.cdn
    proxy_path = hconfig(ConfigEnum.proxy_path)
    res = ""
    if mode == "multi":
        res += "<div class='btn-group'>"
    d=domain.domain
    if "*" in d:
        d=d.replace("*",get_random_string(5,15))

    link = f"https://{d}/{proxy_path}/{uuid}/#{username}"
    link_multi = f"{link}multi"
    # if mode == 'new':
    #     link = f"{link}new"
    text = domain.alias or domain.domain
    color_cls='info'
    if domain.mode in [DomainType.cdn,DomainType.auto_cdn_ip]:
        auto_cdn=(domain.mode==DomainType.auto_cdn_ip) or (domain.cdn_ip and "MTN" in domain.cdn_ip)
        color_cls="success" if auto_cdn else 'warning'
        text = f'<span class="badge badge-secondary" >{"Auto" if auto_cdn else "CDN"}</span> '+text
        

    if mode == "multi":
        res += f"<a class='btn btn-xs btn-secondary' target='_blank' href='{link_multi}' >{_('all')}</a>"
    res += f"<a target='_blank' href='{link}' class='btn btn-xs btn-{color_cls} ltr' ><i class='fa-solid fa-arrow-up-right-from-square d-none'></i> {text}</a>"

    if mode == "multi":
        res += "</div>"
    return res





import psutil
import time
import os
def system_stats():
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # RAM usage
    ram_stats = psutil.virtual_memory()
    ram_used = ram_stats.used/ 1024**3
    ram_total = ram_stats.total/ 1024**3
    
    # Disk usage (in GB)
    disk_stats = psutil.disk_usage('/')
    disk_used = disk_stats.used / 1024**3
    disk_total = disk_stats.total / 1024**3

    hiddify_used = get_folder_size('/opt/hiddify-config/')/ 1024**3
    

    # Network usage
    net_stats = psutil.net_io_counters()
    bytes_sent_cumulative = net_stats.bytes_sent 
    bytes_recv_cumulative = net_stats.bytes_recv 
    bytes_sent = net_stats.bytes_sent - getattr(system_stats, 'prev_bytes_sent', 0)
    bytes_recv = net_stats.bytes_recv - getattr(system_stats, 'prev_bytes_recv', 0)
    system_stats.prev_bytes_sent = net_stats.bytes_sent
    system_stats.prev_bytes_recv = net_stats.bytes_recv
    
    # Total connections and unique IPs
    connections = psutil.net_connections()
    total_connections = len(connections)
    unique_ips = set([conn.raddr.ip for conn in connections if conn.status == 'ESTABLISHED' and conn.raddr])
    total_unique_ips = len(unique_ips)
    
    # Load average
    num_cpus = psutil.cpu_count()
    load_avg = [avg / num_cpus for avg in os.getloadavg()]
    # Return the system information
    return {
        "cpu_percent": cpu_percent,
        "ram_used": ram_used,
        "ram_total": ram_total,
        "disk_used": disk_used,
        "disk_total": disk_total,
        "hiddify_used":hiddify_used,
        "bytes_sent": bytes_sent,
        "bytes_recv": bytes_recv,
        "bytes_sent_cumulative":bytes_sent_cumulative,
        "bytes_recv_cumulative":bytes_recv_cumulative,
        "net_sent_cumulative_GB":bytes_sent_cumulative/ 1024**3,
        "net_total_cumulative_GB":(bytes_sent_cumulative+bytes_recv_cumulative)/ 1024**3,
        "total_connections": total_connections,
        "total_unique_ips": total_unique_ips,
        "load_avg_1min": load_avg[0],
        "load_avg_5min": load_avg[1],
        "load_avg_15min": load_avg[2],
    }


import psutil


def top_processes():
    # Get the process information
    processes = [p for p in psutil.process_iter(['name', 'memory_full_info', 'cpu_percent']) if p.info['name'] != '']
    num_cores = psutil.cpu_count()
    # Calculate memory usage, RAM usage, and CPU usage for each process
    memory_usage = {}
    ram_usage = {}
    cpu_usage = {}
    for p in processes:
        name = p.info['name']
        if "python3" in name or "uwsgi" in name or 'flask' in name:
            name="Hiddify"
        mem_info = p.info['memory_full_info']
        if mem_info is None:
            continue
        mem_usage = mem_info.uss
        cpu_percent = p.info['cpu_percent']/num_cores
        if name in memory_usage:
            memory_usage[name] += mem_usage / (1024 ** 3)
            ram_usage[name] += mem_info.rss / (1024 ** 3)
            cpu_usage[name] += cpu_percent
        else:
            memory_usage[name] = mem_usage / (1024 ** 3)
            ram_usage[name] = mem_info.rss / (1024 ** 3)
            cpu_usage[name] = cpu_percent
    
    # Sort the processes by memory usage, RAM usage, and CPU usage
    top_memory = sorted(memory_usage.items(), key=lambda x: x[1], reverse=True)[:5]
    top_ram = sorted(ram_usage.items(), key=lambda x: x[1], reverse=True)[:5]
    top_cpu = sorted(cpu_usage.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Return the top processes for memory usage, RAM usage, and CPU usage
    return {
        "memory": top_memory,
        "ram": top_ram,
        "cpu": top_cpu
    }


def get_folder_size(folder_path):
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for file in filenames:
                file_path = os.path.join(dirpath, file)
                try:
                    total_size += os.path.getsize(file_path)
                except:
                    pass
    except:
        pass
    return total_size

from .hiddify3 import *
from .hiddify import *
