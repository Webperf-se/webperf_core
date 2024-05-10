# -*- coding: utf-8 -*-

def append_domain_entry(domain, category, value, result):
    if domain not in result:
        result[domain] = {}

    if category not in result[domain]:
        result[domain][category] = []

    if value not in result[domain][category]:
        result[domain][category].append(value)

def has_domain_entry(domain, category, value, result):
    if domain not in result:
        return False

    if category not in result[domain]:
        return False

    if value not in result[domain][category]:
        return False

    return True
