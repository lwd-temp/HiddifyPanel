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


def flash(message, category):
    print(message)
    return flask_flash(Markup(message), category)


def validate_domain_exist(form, field):
    domain = field.data
    if not domain:
        return
    dip = get_domain_ip(domain)
    if dip == None:
        raise ValidationError(
            _("Domain can not be resolved! there is a problem in your domain"))


def reinstall_action(complete_install=False,domain_change=False):
    from hiddifypanel.admin.Actions import Actions
    action=Actions()
    return action.reinstall(complete_install=complete_install, domain_changed=domain_changed)

def check_need_reset(old_configs,do=False):
    restart_mode = ''
    for c in old_configs:
        if old_configs[c] != hconfig(c) and c.apply_mode():
            if restart_mode != 'reinstall':
                restart_mode = c.apply_mode()

    # do_full_install=old_config[ConfigEnum.telegram_lib]!=hconfig(ConfigEnum.telegram_lib)

    if not (do and restart_mode =='reinstall'):
        return flash_config_success(restart_mode=restart_mode, domain_changed=False)
        
    return reinstall_action(complete_install=True, domain_changed=domain_changed)


def format_timedelta(delta, add_direction=True,granularity="days"):
    res=delta.days
    print(delta.days)
    locale=g.locale if g and hasattr(g, "locale") else hconfig(ConfigEnum.admin_lang)
    if granularity=="days" and delta.days==0:
        res= _("0 - Last day")
    elif delta.days < 7 or delta.days >= 60:
        res= babel_format_timedelta(delta, threshold=1, add_direction=add_direction, locale=locale)
    elif delta.days < 60:
        res= babel_format_timedelta(delta, granularity="day", threshold=10, add_direction=add_direction, locale=locale)
    return res












def get_child(unique_id):
    child_id=0  
    if unique_id is None:
        child_id= 0
    else:
        child = Child.query.filter(Child.unique_id == str(unique_id)).first()
        if not child:
            child=Child(unique_id=str(unique_id))
            db.session.add(child)
            db.session.commit()
            child = Child.query.filter(Child.unique_id == str(unique_id)).first()
        child_id= child.id
    return child_id



def domain_dict(d):
    return {
        'domain': d.domain,
        'mode': d.mode,
        'alias': d.alias,
        'child_unique_id': d.child.unique_id if d.child else '',
        'cdn_ip': d.cdn_ip,
        'show_domains': [dd.domain for dd in d.show_domains]
    }


def parent_domain_dict(d):
    return {
        'domain': d.domain,
        'show_domains': [dd.domain for dd in d.show_domains]
    }

def date_to_json(d):
    return d.strftime("%Y-%m-%d") if d else None

def user_dict(d):
    return {
        'uuid':d.uuid,
        'name':d.name,
        'last_online':str(d.last_online),
        'usage_limit_GB':d.usage_limit_GB,
        'package_days':d.package_days,
        'mode':d.mode,
        'start_date':date_to_json(d.start_date),
        'current_usage_GB':d.current_usage_GB,
        'last_reset_time':date_to_json(d.last_reset_time),
        'comment':d.comment
    }


def proxy_dict(d):
    return {
        'name': d.name,
        'enable': d.enable,
        'proto': d.proto,
        'l3': d.l3,
        'transport': d.transport,
        'cdn': d.cdn,
        'child_unique_id': d.child.unique_id if d.child else ''
    }

def config_dict(d):
    return {
        'key': d.key,
        'value': d.value,
        'child_unique_id': d.child.unique_id if d.child else ''
    }


def dump_db_to_dict():
    return {"users": [user_dict(u) for u in User.query.all()],
            "domains": [domain_dict(u) for u in Domain.query.all()],
            "proxies": [proxy_dict(u) for u in Proxy.query.all()],
            "parent_domains": [] if not hconfig(ConfigEnum.license) else [parent_domain_dict(u) for u in ParentDomain.query.all()],
            "hconfigs": [*[config_dict(u) for u in BoolConfig.query.all()],
                         *[config_dict(u) for u in StrConfig.query.all()]]
            }
def add_or_update_parent_domains(commit=True,**parent_domain):
    dbdomain = ParentDomain.query.filter(
         ParentDomain.domain == parent_domain['domain']).first()
    if not dbdomain:
        dbdomain = ParentDomain(domain=parent_domain['domain'])
        db.session.add(dbdomain)
    show_domains = parent_domain.get('show_domains', [])
    dbdomain.show_domains = Domain.query.filter(
        Domain.domain.in_(show_domains)).all()
    if commit:
        db.session.commit()

from .hiddify import *
from .hiddify2 import *