from hiddifypanel.models import  *
from hiddifypanel.panel.database import db
import sys
from hiddifypanel import Events        



from dateutil import relativedelta
import datetime

from hiddifypanel.panel import hiddify
import random
import uuid
import urllib
import string
from .init_db2 import *
def init_db():
    db.create_all()   
    
    try:
        db.engine.execute(f'update proxy set transport="WS" where transport = "ws"')
        db.engine.execute(f'DELETE from proxy where transport = "h1"')
    except:
        pass
    if hconfig(ConfigEnum.license):
        add_column(ParentDomain.alias)
    add_column(User.start_date)
    add_column(User.package_days)
    add_column(Child.unique_id)
    add_column(Domain.alias)
    add_column(Domain.child_id)
    add_column(Proxy.child_id)
    add_column(BoolConfig.child_id)
    add_column(StrConfig.child_id)

    if len(Domain.query.all())!=0 and BoolConfig.query.count()==0:
        db.engine.execute(f'DROP TABLE bool_config')
        db.engine.execute(f'ALTER TABLE bool_config_old RENAME TO bool_config')
    if len(Domain.query.all())!=0 and StrConfig.query.count()==0:
        db.engine.execute(f'DROP TABLE str_config')
        db.engine.execute(f'ALTER TABLE str_config_old RENAME TO str_config')

    try:
        add_column(User.monthly)
        db.engine.execute('ALTER TABLE user RENAME COLUMN monthly_usage_limit_GB TO usage_limit_GB')       
    except:
        pass
    try:
        db.engine.execute(f'update str_config set child_id=0 where child_id is NULL')
        db.engine.execute(f'update bool_config set child_id=0 where child_id is NULL')
        db.engine.execute(f'update domain set child_id=0 where child_id is NULL')
        db.engine.execute(f'update proxy set child_id=0 where child_id is NULL')
    except:
        pass
    
    add_column(Domain.cdn_ip)
    db_version=int(hconfig(ConfigEnum.db_version) or 0) 
    start_version=db_version
    # print(f"Current DB version is {db_version}")
    if not Child.query.filter(Child.id==0).first():
        print(Child.query.filter(Child.id==0).first())
        db.session.add(Child(unique_id="self",id=0))
        db.session.commit()
    

    for ver in range(1,40):
        if ver<=db_version:continue
        
        db_action=sys.modules[__name__].__dict__.get(f'_v{ver}',None)
        if not db_action:continue
        if start_version==0 and ver==10:continue

        print(f"Updating db from version {db_version}")
        db_action()
        Events.db_init_event.notify(db_version=db_version)
        print(f"Updated successfuly db from version {db_version} to {ver}")
        
        db_version=ver
        db.session.commit()
        set_hconfig(ConfigEnum.db_version,db_version,commit=False)
    
    
    db.session.commit()
    return BoolConfig.query.all()

def _v27():
    # add_config_if_not_exist(ConfigEnum.cloudflare, "")
    set_hconfig(ConfigEnum.netdata, False)
def _v26():
    add_config_if_not_exist(ConfigEnum.cloudflare, "")

def _v25():
    add_config_if_not_exist(ConfigEnum.country, "ir")
    add_config_if_not_exist(ConfigEnum.parent_panel, "")
    add_config_if_not_exist(ConfigEnum.is_parent, False)
    add_config_if_not_exist(ConfigEnum.license, "")
    


def _v21():
    db.session.bulk_save_objects(get_proxy_rows_v1())


def _v20():
    if hconfig(ConfigEnum.domain_fronting_domain):
        fake_domains=[hconfig(ConfigEnum.domain_fronting_domain)]
        
        direct_domain=Domain.query.filter(Domain.mode in [DomainType.direct,DomainType.relay]).first()
        if direct_domain:
            direct_host=direct_domain.domain
        else:
            direct_host=hiddify.get_ip(4)

        for fd in fake_domains:
            if not Domain.query.filter(Domain.domain==fd).first():
                db.session.add(Domain(domain=fd,mode='fake',alias='moved from domain fronting',cdn_ip=direct_host))    

def _v19():
    set_hconfig(ConfigEnum.path_trojan,get_random_string(7,15))
    set_hconfig(ConfigEnum.path_vless,get_random_string(7,15))
    set_hconfig(ConfigEnum.path_vmess,get_random_string(7,15))
    set_hconfig(ConfigEnum.path_ss,get_random_string(7,15))
    set_hconfig(ConfigEnum.path_grpc,get_random_string(7,15))
    set_hconfig(ConfigEnum.path_tcp,get_random_string(7,15))
    set_hconfig(ConfigEnum.path_ws,get_random_string(7,15))
    

def _v17():
    for u in User.query.all():
        if u.expiry_time:
            if not u.package_days:
                if not u.last_reset_time:
                    u.package_days=(u.expiry_time-datetime.date.today()).days
                    u.start_date=datetime.date.today()
                else:
                    u.package_days=(u.expiry_time-u.last_reset_time).days
                    u.start_date=u.last_reset_time
            u.expiry_time=None
            
            

def _v16():
    
    add_config_if_not_exist(ConfigEnum.tuic_enable,False)
    add_config_if_not_exist(ConfigEnum.shadowtls_enable,False)
    add_config_if_not_exist(ConfigEnum.shadowtls_fakedomain,"en.wikipedia.org")


        

def _v14():
    add_config_if_not_exist(ConfigEnum.utls,"chrome")
    
def _v13():
    add_config_if_not_exist(ConfigEnum.telegram_bot_token,"")
    add_config_if_not_exist(ConfigEnum.package_mode,"release")

def _v12():
    db.engine.execute(f'drop TABLE child')
    db.create_all()
    db.session.add(Child(id=0,unique_id="default"))

def _v11():
    add_column(User.last_online)




def _v1():
        
        next10year = datetime.date.today() + relativedelta.relativedelta(years=6)
        external_ip=hiddify.get_ip(4)
        rnd_domains=get_random_domains(5)
        data = [
            StrConfig(key=ConfigEnum.db_version,value=1),
            User(name="default",usage_limit_GB=3000,package_days=3650,mode=UserMode.weekly),
            Domain(domain=external_ip+".sslip.io",mode=DomainType.direct),
            StrConfig(key=ConfigEnum.admin_secret,value=str(uuid.uuid4())),
            StrConfig(key=ConfigEnum.http_ports,value="80"),
            StrConfig(key=ConfigEnum.tls_ports,value="443"),
            
            StrConfig(key=ConfigEnum.decoy_domain,value=rnd_domains[0]),
            StrConfig(key=ConfigEnum.proxy_path,value=get_random_string()),
            BoolConfig(key=ConfigEnum.firewall,value=True),
            BoolConfig(key=ConfigEnum.netdata,value=True),
            StrConfig(key=ConfigEnum.lang,value='fa'),
            
            BoolConfig(key=ConfigEnum.block_iran_sites,value=True),
            BoolConfig(key=ConfigEnum.allow_invalid_sni,value=True),
            BoolConfig(key=ConfigEnum.kcp_enable,value=False),
            StrConfig(key=ConfigEnum.kcp_ports,value="88"),
            BoolConfig(key=ConfigEnum.auto_update,value=True),
            BoolConfig(key=ConfigEnum.speed_test,value=True),
            BoolConfig(key=ConfigEnum.only_ipv4,value=False),

            BoolConfig(key=ConfigEnum.vmess_enable,value=True),
            BoolConfig(key=ConfigEnum.http_proxy_enable,value=True),
            StrConfig(key=ConfigEnum.shared_secret,value=str(uuid.uuid4())),

            BoolConfig(key=ConfigEnum.telegram_enable,value=True),
            # StrConfig(key=ConfigEnum.telegram_secret,value=uuid.uuid4().hex),
            StrConfig(key=ConfigEnum.telegram_adtag,value=""),
            StrConfig(key=ConfigEnum.telegram_fakedomain, value=rnd_domains[1]),
 
            BoolConfig(key=ConfigEnum.ssfaketls_enable,value=False),
            # StrConfig(key=ConfigEnum.ssfaketls_secret,value=str(uuid.uuid4())),
            StrConfig(key=ConfigEnum.ssfaketls_fakedomain, value=rnd_domains[2]),

            BoolConfig(key=ConfigEnum.shadowtls_enable,value=False),
            # StrConfig(key=ConfigEnum.shadowtls_secret,value=str(uuid.uuid4())),
            StrConfig(key=ConfigEnum.shadowtls_fakedomain, value=rnd_domains[3]),

            BoolConfig(key=ConfigEnum.ssr_enable,value=False),
            # StrConfig(key=ConfigEnum.ssr_secret,value=str(uuid.uuid4())),
            StrConfig(key=ConfigEnum.ssr_fakedomain, value=rnd_domains[4]),

            BoolConfig(key=ConfigEnum.tuic_enable,value=False),
            StrConfig(key=ConfigEnum.tuic_port,value=3048),

            BoolConfig(key=ConfigEnum.domain_fronting_tls_enable,value=False),
            BoolConfig(key=ConfigEnum.domain_fronting_http_enable,value=False),
            StrConfig(key=ConfigEnum.domain_fronting_domain,value=""),

            # BoolConfig(key=ConfigEnum.torrent_block,value=False),

            *get_proxy_rows_v1()
        ]
        fake_domains=['speedtest.net']
        for fd in fake_domains:
            if not Domain.query.filter(Domain.domain==fd).first():
                db.session.add(Domain(domain=fd,mode='fake',alias='fake domain',cdn_ip=external_ip))
        # for c in ConfigEnum:
        #     if c in [d.key for d in data if type(d) in [BoolConfig,StrConfig]]:
        #         continue
        #     if c.type()==bool:
        #         data.append(BoolConfig(key=c,value=False))
        #     else:
        #         data.append(StrConfig(key=c,value=""))
                    

        
        db.session.bulk_save_objects(data)
