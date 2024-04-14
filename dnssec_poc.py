# -*- coding: utf-8 -*-
import getopt
import sys
import sys
import config
from tests.utils import *
import dns.message

def main(argv):
    """
    WebPerf Core - Software update
    """

    try:
        opts, args = getopt.getopt(argv, "hu:t:i:o:rA:D:L:", [
                                   "help", "url=", "test=", "input=", "output=", "review", "report", "addUrl=", "deleteUrl=", "language=", "input-skip=", "input-take="])
    except getopt.GetoptError:
        print(main.__doc__)
        sys.exit(2)

    if (opts.__len__() == 0):
        show_help = True

    url = None
    #url = 'https://eskilstuna.se'
    #url = 'https://polisen.se'
    #url = 'https://www.gotene.se'
    
    for opt, arg in opts:
        if opt in ('-h', '--help'):  # help
            show_help = True
        elif opt in ("-u", "--url"):  # site url
            url = arg

    if url == None:
        print('no url specified')
    else:
        print('using url:', url)



    # We must take in consideration "www." subdomains...
    o = urllib.parse.urlparse(url)
    hostname = o.hostname

    # if hostname.startswith('www.'):
    #     url = url.replace(hostname, hostname[4:])

    o = urllib.parse.urlparse(url)
    hostname = o.hostname

    # IMPROVE DNSSEC QUERIES:
    # Analyzing polisen.se
    # Querying polisen.se/NS (referral)...
    # Querying polisen.se/NS (auth, detecting cookies)...
    # Querying polisen.se/A...
    # Preparing 0x20 query PoLISEN.SE/SOA...
    # Preparing DNS cookie diagnostic query polisen.se/SOA...
    # Preparing query polisen.se/NSEC3PARAM...
    # Preparing query hfsp0za3wj.polisen.se/A (NXDOMAIN)...
    # Preparing query polisen.se/CNAME (NODATA)...
    # Preparing query polisen.se/MX...
    # Preparing query polisen.se/TXT...
    # Preparing query polisen.se/SOA...
    # Preparing query polisen.se/DNSKEY...
    # Preparing query polisen.se/DS...
    # Preparing query polisen.se/AAAA...
    # Executing queries...
    # Analysis Complete


    print('NS')
    response = testdns('{0}'.format(hostname), dns.rdatatype.NS, True)
    print('A')
    response = testdns('{0}'.format(hostname), dns.rdatatype.A, True)
    print('SOA')
    response = testdns('{0}'.format(hostname), dns.rdatatype.SOA, True)
    print('NSEC3PARAM')
    response = testdns('{0}'.format(hostname), dns.rdatatype.NSEC3PARAM, True)
    print('CNAME')
    response = testdns('{0}'.format(hostname), dns.rdatatype.CNAME, True)
    print('MX')
    response = testdns('{0}'.format(hostname), dns.rdatatype.MX, True)
    print('TXT')
    response = testdns('{0}'.format(hostname), dns.rdatatype.TXT, True)
    print('DNSKEY')
    response = testdns('{0}'.format(hostname), dns.rdatatype.DNSKEY, True)
    print('DS')
    response = testdns('{0}'.format(hostname), dns.rdatatype.DS, True)
    print('AAAA')
    response = testdns('{0}'.format(hostname), dns.rdatatype.AAAA, True)



def validate_dnssec(domain, domain_entry):
    # subdomain = 'static.internetstiftelsen.se'
    # domain = 'internetstiftelsen.se'
    print('  ', domain)

    # Get the name object for 'www.example.com'
    name = dns.name.from_text(domain)

    # response_dnskey_ns = testdns(name, dns.rdatatype.NS, True)
    # response_dnskey_dnssec = testdns(name, dns.rdatatype.DNSKEY, True)
    # response_dnskey_dnssec = testdns(name, dns.rdatatype.DNSKEY, False)
    # response_dnskey_cname = testdns(name, dns.rdatatype.CNAME, True)
    # response_dnskey_a = testdns(name, dns.rdatatype.A, True)
    # response_dnskey_aaaa = testdns(name, dns.rdatatype.AAAA, True)
    # response_dnskey_soa = testdns(name, dns.rdatatype.SOA, True)
    # response_dnskey_txt = testdns(name, dns.rdatatype.TXT, True)
    # response_dnskey_mx = testdns(name, dns.rdatatype.MX, True)
    # response_dnskey_ds = testdns(name, dns.rdatatype.DS, True)


    # Get the DNSKEY for the domain
    # dnskeys = []
    # if dnskeys_response.rcode() != 0:
    #     # HANDLE QUERY FAILED (SERVER ERROR OR NO DNSKEY RECORD)
    #     print('\t\tA.1', dnskeys_response.rcode())
    #     domain_entry['features'].append('DNSSEC-NO-DNSKEY(S):{0}'.format(nsname))
    #     return domain_entry
    #     # continue
    # else:
    #     print('\t\tA.2', dnskeys_response.rcode())
    #     domain_entry['features'].append('DNSSEC-DNSKEYS:{0}'.format(nsname))
    #     dnskeys = dnskeys_response.answer
    
    # # Get the DS for the domain
    # ds_answer = dns.resolver.resolve(subdomain, dns.rdatatype.DS)

    # request = dns.message.make_query(domain, dns.rdatatype.A, want_dnssec=True)
    # request = dns.message.make_query(domain, dns.rdatatype.DNSKEY, want_dnssec=True)

    domain_name = dns.name.from_text(domain)
    request = dns.message.make_query(domain_name, dns.rdatatype.DNSKEY, want_dnssec=True)
    # request = dns.message.make_query(domain_name, dns.rdatatype.A, want_dnssec=True)
    #request = dns.message.make_query(domain_name, dns.rdatatype.A, want_dnssec=True)
    response = dns.query.udp(request, '8.8.8.8')

    nsname = '8.8.8.8'

    if response.rcode() != 0:
        # HANDLE QUERY FAILED (SERVER ERROR OR NO DNSKEY RECORD)
        print('\tERROR, RCODE is INVALID:', response.rcode())
        domain_entry['features'].append('DNSSEC-NO-RCODE:{0}'.format(nsname))
        return domain_entry
        # continue
    else:
        print('\tVALID RCODE')
        domain_entry['features'].append('DNSSEC-RCODE:{0}'.format(nsname))

    dnskey = None
    rrsig = None

    # print('E', answer)
    if len(response.answer) < 2:
        # SOMETHING WENT WRONG
        print('\tWARNING, to few answers:', len(response.answer))

        # find the associated RRSIG RRset
        rrsig = None

        print('\t\tQ.answer', response.answer)
        print('\t\tQ.authority', response.authority)
        print('\t\tQ.additional', response.additional)


        print('\tRRSET(s):')
        for rrset in response.answer + response.authority + response.additional:
            print('\t\tRRSET:', rrset)
            if rrset.rdtype == dns.rdatatype.RRSIG:
                rrsig = rrset
                print('\t\t\tRRSIG found')
                domain_entry['features'].append('DNSSEC-RRSIG-FOUND')
            if rrset.rdtype == dns.rdatatype.DNSKEY:
                dnskey = rrset
                print('\t\tDNSKEY found')
                domain_entry['features'].append('DNSSEC-DNSKEY-FOUND')

        domain_entry['features'].append('DNSSEC-NO-ANSWER:{0}'.format(nsname))
        return domain_entry
        # continue
    else:
        print('\tParsing Answers, nof answers:', len(response.answer))

        # find DNSKEY and RRSIG in answer
        # dnskey = None
        # rrsig = None
        for rrset in response.answer:
            print('\tRRSET', rrset)
            if dnskey == None and rrset.rdtype == dns.rdatatype.DNSKEY:
                dnskey = rrset
                print('\t\tDNSKEY found')
                domain_entry['features'].append('DNSSEC-DNSKEY-FOUND')
            elif rrsig == None and rrset.rdtype == dns.rdatatype.RRSIG:
                rrsig = rrset
                print('\t\tRRSIG found')
                domain_entry['features'].append('DNSSEC-RRSIG-FOUND')

        domain_entry['features'].append('DNSSEC-ANSWER:{0}'.format(nsname))

        # # validate the answer
        # if rrsig is not None:                       

    # if dnskey == None and len(dnskeys) > 0:
    #     print('\tNO DNS KEY')
    #     dnskey = dnskeys[0]
    print('\n\n')
    print('\t# {0} - DNSKEY ='.format(domain), dnskey)
    print('\t# {0} - RRSIG = '.format(domain), rrsig)

    # import dns.zone

    # Validate the DNSKEY with the DS
    if dnskey == None:
        print('\tRETRY DNSKEY')
        validate_rrsig_no_dnskey(domain, rrsig, domain_entry)
    else:
        validate_dnskey_and_rrsig(domain, dnskey, rrsig, domain_entry)
    # try:
    #     dns.dnssec.validate(dnskey, rrsig, dnskey)
    #     # dns.dnssec.validate(dnskey, rrsig, {name: dnskey})
    #     # dns.dnssec.validate(dnskey, rrsig)
    #     print("DNSSEC validation passed")
    # except dns.dnssec.ValidationFailure as vf:
    #     print('DNSSEC VALIDATION FAIL', vf)
    #     domain_entry['features'].append('DNSSEC-FALIED-VALIDATION:{0}'.format(nsname))
    # else:
    #     domain_entry['features'].append('DNSSEC')
    #     print('\t\tG.3 - VALIDATION SUCCESS\r\n')

    # print('\t3')


def testdns(key, datatype, use_dnssec):
    print('\ttestdns', key, datatype, use_dnssec)
    cache_key = 'dnslookup://{0}#{1}#{2}'.format(key, datatype, use_dnssec)
    if has_cache_file(cache_key, True, CACHE_TIME_DELTA):
        cache_path = get_cache_path_for_file(cache_key, True)
        print('\t- Using dnslookup cache')
        response = dns.message.from_file(cache_path)
        print('\t- response:\n\t\t{0}'.format(response.to_text().replace('\n', '\n\t\t')))
        return response

    try:
        query = None
        # Create a query for the 'www.example.com' domain
        if use_dnssec:
            query = dns.message.make_query(key, datatype, want_dnssec=True)
        else:
            query = dns.message.make_query(key, datatype, want_dnssec=False)

        print('\t- dnslookup live')
        # Send the query and get the response
        response = dns.query.udp(query, '8.8.8.8')

        if response.rcode() != 0:
            # HANDLE QUERY FAILED (SERVER ERROR OR NO DNSKEY RECORD)
            print('\t\tERROR, RCODE is INVALID:', response.rcode())
            return None

        print('\t- response:\n\t\t', response.to_text().replace('\n', '\n\t\t'))

        text_response = response.to_text()
        set_cache_file(cache_key, text_response, True)

        time.sleep(5)

        return response

    except dns.dnssec.ValidationFailure as vf:
        print('\t\tDNS FAIL', vf)
    except Exception as ex:
        print('\t\tDNS GENERAL FAIL', ex)

    return None

def validate_rrsig_no_dnskey(domain, rrsig, domain_entry):
    nsname = '8.8.8.8'
    try:
        #dns.dnssec.validate(dnskey, rrsig, dnskey)
        import dns.message
        # Create a query for the 'www.example.com' domain
        query = dns.message.make_query(domain, dns.rdatatype.A, want_dnssec=True)

        # Send the query and get the response
        response = dns.query.udp(query, '8.8.8.8')

        # Get the answer section from the response
        answer_section = response.answer

        # Get the name object for 'www.example.com'
        name = dns.name.from_text(domain)

        # Get the RRset from the answer section
        rrset = response.get_rrset(answer_section, name, dns.rdataclass.IN, dns.rdatatype.DNSKEY)        

        # name = dns.name.from_text(domain)
        # Assuming 'answers' is an dns.resolver.Answer object containing the DNSKEY records
        # rrset = answers.get_rrset(dnskeys, name, dns.rdataclass.IN, dns.rdatatype.DNSKEY)
        dns.dnssec.validate(rrset, rrsig, {name: rrset})        
        # name = dns.name.from_text(domain)
        # dns.dnssec.validate(dnskey, rrsig, {name, dnskey})
        # dns.dnssec.validate(dnskey, rrsig)
        print("\t\t\tDNSSEC validation passed")
    except dns.dnssec.ValidationFailure as vf:
        print('\t\t\tDNSSEC VALIDATION FAIL', vf)
        domain_entry['features'].append('DNSSEC-FALIED-VALIDATION:{0}'.format(nsname))
    except Exception as ex:
        print('\t\t\tDNSSEC GENERAL FAIL', ex)
        domain_entry['features'].append('DNSSEC-FALIED-VALIDATION:{0}'.format(nsname))
    else:
        domain_entry['features'].append('DNSSEC')
        print('\t\tG.3 - VALIDATION SUCCESS\r\n')

def validate_dnskey_and_rrsig(domain, dnskey, rrsig, domain_entry):
    nsname = '8.8.8.8'
    try:
        #dns.dnssec.validate(dnskey, rrsig, dnskey)
        name = dns.name.from_text(domain)
        dns.dnssec.validate(dnskey, rrsig, {name: dnskey})
        # dns.dnssec.validate(dnskey, rrsig)
        print("\t\t\tDNSSEC validation passed")
    except dns.dnssec.ValidationFailure as vf:
        print('\t\t\tDNSSEC VALIDATION FAIL', vf)
        domain_entry['features'].append('DNSSEC-FALIED-VALIDATION:{0}'.format(nsname))
    else:
        domain_entry['features'].append('DNSSEC')
        print('\t\tG.3 - VALIDATION SUCCESS\r\n')

def check_dnssec(hostname, result_dict):
    print('DNSSEC')
    new_entries = []
    for domainA in result_dict.keys():
        try:
            domain = domainA
            domain_entry = result_dict[domain]

            if hostname != domain:
                domain_entry['features'].append('DNSSEC-IGNORE')
                continue
            # print('# {0}'.format(domain))
            validate_dnssec(domain, domain_entry)

        except Exception as e:
            print('DNSSEC EXCEPTION', e)
    for entry in new_entries:
        name = entry['name']
        del entry['name']
        result_dict[name] = entry
        
    return result_dict

def check_dnssec2(hostname, result_dict):
    print('DNSSEC')

    # NOTE: https://www.cloudflare.com/dns/dnssec/how-dnssec-works/
    # NOTE: https://github.com/dnsviz/dnsviz/blob/master/dnsviz/resolver.py
    
    # TODO: DNSSEC (BUT NOT ON ALL NAMESERVERS: internetstiftelsen.se)

    # To facilitate signature validation, DNSSEC adds a few new DNS record types4:

    # RRSIG - Contains a cryptographic signature
    # DNSKEY - Contains a public signing key
    # DS - Contains the hash of a DNSKEY record
    # NSEC and NSEC3 - For explicit denial-of-existence of a DNS record
    # CDNSKEY and CDS - For a child zone requesting updates to DS record(s) in the parent zone
    # get nameservers for target domain




    # IMPROVE DNSSEC QUERIES:
    # Analyzing polisen.se
    # Querying polisen.se/NS (referral)...
    # Querying polisen.se/NS (auth, detecting cookies)...
    # Querying polisen.se/A...
    # Preparing 0x20 query PoLISEN.SE/SOA...
    # Preparing DNS cookie diagnostic query polisen.se/SOA...
    # Preparing query polisen.se/NSEC3PARAM...
    # Preparing query hfsp0za3wj.polisen.se/A (NXDOMAIN)...
    # Preparing query polisen.se/CNAME (NODATA)...
    # Preparing query polisen.se/MX...
    # Preparing query polisen.se/TXT...
    # Preparing query polisen.se/SOA...
    # Preparing query polisen.se/DNSKEY...
    # Preparing query polisen.se/DS...
    # Preparing query polisen.se/AAAA...
    # Executing queries...
    # Analysis Complete
    

    # Analyzing eskilstuna.se
    # Querying eskilstuna.se/NS (referral)...
    # Querying eskilstuna.se/NS (auth, detecting cookies)...
    # Querying eskilstuna.se/A...
    # Preparing 0x20 query EsKILStUNa.sE/SOA...
    # Preparing DNS cookie diagnostic query eskilstuna.se/SOA...
    # Preparing query eskilstuna.se/NSEC3PARAM...
    # Preparing query 5gweac9poq.eskilstuna.se/A (NXDOMAIN)...
    # Preparing query eskilstuna.se/CNAME (NODATA)...
    # Preparing query eskilstuna.se/MX...
    # Preparing query eskilstuna.se/TXT...
    # Preparing query eskilstuna.se/SOA...
    # Preparing query eskilstuna.se/DNSKEY...
    # Preparing query eskilstuna.se/DS...
    # Preparing query eskilstuna.se/AAAA...
    # Executing queries...
    # Analyzing www.eskilstuna.se
    # Querying www.eskilstuna.se/NS (referral)...
    # Preparing query www.eskilstuna.se/A...
    # Preparing query www.eskilstuna.se/AAAA...
    # Executing queries...
    # Analysis Complete    



    import dns.zone

    new_entries = []
    for domainA in result_dict.keys():
        try:
            domain = domainA
            domain_entry = result_dict[domain]

            if hostname != domain:
                domain_entry['features'].append('DNSSEC-IGNORE')
                continue

            # validate_dnssec(domain)
            print('# {0}'.format(domain))

            # if 'svanalytics.piwik.pro' == domainA:
            #     domain = 'piwik.pro'
            #     domain_entry = {
            #         'name': domain,
            #         'protocols': [],
            #         'schemes': [],
            #         'ip-versions': [],
            #         'transport-layers': [],
            #         'features': [],
            #         'urls': []
            #     }
            #     new_entries.append(domain_entry)
            # domain_entry = result_dict[domain]

            dnskeys = dns_lookup(domain, dns.rdatatype.DNSKEY)
            # print('\t\tDNSKEY', dnskey)
            print('\tDNSKEY(S):', len(dnskeys))
            if len(dnskeys) == 0:
                domain_entry['features'].append('DNSSEC-NO-DNSKEY')
            else:
                domain_entry['features'].append('DNSSEC-DNSKEY')

            import dns.resolver

            resolver = dns.resolver.Resolver()
            # resolver.nameservers = [ '8.8.8.8' ]

            response = resolver.query('{0}.'.format(domain), dns.rdatatype.NS)
            nsnames = dns_lookup('{0}.'.format(domain), dns.rdatatype.NS)
            print('\tNAMESERVER(S):', len(nsnames))

            # we'll use the first nameserver in this example
            # nof_nsnames = len(response.rrset)
            #nsnames = []
            for nsname in nsnames:
                #nsnames.append(entry.to_text())

                # print('A', nsnames)
                # nsname = entry.to_text()  # name
                #nsname = response.rrset[1].to_text()  # name
                print('\tA', nsname)

                # test = dns_lookup(domain, dns.rdatatype.RRSIG)
                # print('\t\tRRSIG', test)


                # get DNSKEY for zone
                # ADDITIONAL_RDCLASS = 4096
                # request = dns.message.make_query('{0}.'.format(domain), dns.rdatatype.A, want_dnssec=True)
                # request.flags |= dns.flags.AD
                # request.find_rrset(request.additional, dns.name.root, ADDITIONAL_RDCLASS,
                #                 dns.rdatatype.OPT, create=True, force_unique=True)                
                request = dns.message.make_query(domain, dns.rdatatype.DNSKEY, want_dnssec=True)
                # request = dns.message.make_query(domain, dns.rdatatype.A, want_dnssec=True)
                # request = dns.message.make_query(domain, dns.rdatatype.DNSKEY)
                # name = dns.name.from_text('{0}.'.format(domain))
                name = dns.name.from_text(domain)
                print('\t\tA.1', name)
                # print('\t\tA.1.1', domain_entry)


                if 'IPv4' in domain_entry['ip-versions'] or 'IPv4*' in domain_entry['ip-versions']:
                    # print('\t\tA.2')
                    response = resolver.query(nsname, dns.rdatatype.A)
                    print('\t\tA.3', response)
                    nsaddr = response.rrset[0].to_text()  # IPv4

                    print('\t\tA.4', nsaddr)

                    # send the query
                    response = dns.query.udp(request, nsaddr)
                    # response = dns.query.udp(request, '8.8.8.8')

                    # print('\t\tA.5', response)
                    print('\t\tA.5')

                    if response.rcode() != 0:
                        # HANDLE QUERY FAILED (SERVER ERROR OR NO DNSKEY RECORD)
                        print('\t\tD.1', response.rcode())
                        domain_entry['features'].append('DNSSEC-NO-RCODE:{0}'.format(nsname))
                        continue
                    else:
                        print('\t\tD.2', response.rcode())
                        domain_entry['features'].append('DNSSEC-RCODE:{0}'.format(nsname))

                    # answer should contain two RRSET: DNSKEY and RRSIG (DNSKEY)
                    # answer = response.answer
                    dnskey = None
                    rrsig = None

                    # print('E', answer)
                    if len(response.answer) < 2:
                        # SOMETHING WENT WRONG
                        print('\t\tE.1', len(response.answer))

                        # find the associated RRSIG RRset
                        rrsig = None

                        print('\t\t\tQ.answer', response.answer)
                        print('\t\t\tQ.authority', response.authority)
                        print('\t\t\tQ.additional', response.additional)

                        for rrset in response.answer + response.authority + response.additional:
                            print('\t\tE.2', rrset)
                            if rrset.rdtype == dns.rdatatype.RRSIG:
                                rrsig = rrset
                                break


                        domain_entry['features'].append('DNSSEC-NO-ANSWER:{0}'.format(nsname))
                        continue
                    else:
                        print('\t\tE.2', len(response.answer))

                        # find DNSKEY and RRSIG in answer
                        dnskey = None
                        rrsig = None
                        for rrset in response.answer:
                            if rrset.rdtype == dns.rdatatype.DNSKEY:
                                dnskey = rrset
                            elif rrset.rdtype == dns.rdatatype.RRSIG:
                                rrsig = rrset
                        domain_entry['features'].append('DNSSEC-ANSWER:{0}'.format(nsname))

                        # # validate the answer
                        # if rrsig is not None:                       

                    if dnskey == None and len(dnskeys) > 0:
                        dnskey = dnskeys[0]

                    # the DNSKEY should be self-signed, validate it
                    try:
                        # print('F')
                        # dns.dnssec.validate(answer[0], answer[1], {name: answer[0]})

                        print('\t\tF.1', dnskey)
                        print('\t\tF.2', rrsig)


                        # dns.dnssec.validate(answer, rrsig)
                        dns.dnssec.validate(dnskey, rrsig, {name: dnskey})
                        print('\t\tG.1\r\n')
                    except dns.dnssec.ValidationFailure as vf:
                        # BE SUSPICIOUS
                        a = False
                        # print('G VALIDATION FAIL')
                        print('DNSSEC VALIDATION FAIL', vf)
                        domain_entry['features'].append('DNSSEC-FALIED-VALIDATION:{0}'.format(nsname))
                        print('\t\tG.2 - VALIDATION FAIL\r\n')
                    else:
                        # WE'RE GOOD, THERE'S A VALID DNSSEC SELF-SIGNED KEY FOR example.com
                        # print('G VALIDATION SUCCESS')
                        domain_entry['features'].append('DNSSEC')
                        domain_entry['features'].append('DNSSEC:{0}'.format(nsname))
                        print('\t\tG.3 - VALIDATION SUCCESS\r\n')
                        
                        # a = True

            # if 'IPv6' in result_dict[domain]['ip-versions'] or 'IPv6*' in result_dict[domain]['ip-versions']:
            #     b = 1
            #     print('B IPv6')
        except Exception as e:
            print('DNSSEC EXCEPTION', e)

    for entry in new_entries:
        name = entry['name']
        del entry['name']
        result_dict[name] = entry
        
    return result_dict


"""
If file is executed on itself then call a definition, mostly for testing purposes
"""
if __name__ == '__main__':
    main(sys.argv[1:])
