#!/usr/bin/env python

# Unix SMB/CIFS implementation.
# Copyright (C) Kai Blin  <kai@samba.org> 2011
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import sys
import struct
import random
from samba import socket
import samba.ndr as ndr
import samba.dcerpc.dns as dns
from samba.tests import TestCase

class DNSTest(TestCase):

    def assert_dns_rcode_equals(self, packet, rcode):
        "Helper function to check return code"
        p_errcode = packet.operation & 0x000F
        self.assertEquals(p_errcode, rcode, "Expected RCODE %s, got %s" % \
                            (rcode, p_errcode))

    def assert_dns_opcode_equals(self, packet, opcode):
        "Helper function to check opcode"
        p_opcode = packet.operation & 0x7800
        self.assertEquals(p_opcode, opcode, "Expected OPCODE %s, got %s" % \
                            (opcode, p_opcode))

    def make_name_packet(self, opcode, qid=None):
        "Helper creating a dns.name_packet"
        p = dns.name_packet()
        if qid is None:
            p.id = random.randint(0x0, 0xffff)
        p.operation = opcode
        p.questions = []
        return p

    def finish_name_packet(self, packet, questions):
        "Helper to finalize a dns.name_packet"
        packet.qdcount = len(questions)
        packet.questions = questions

    def make_name_question(self, name, qtype, qclass):
        "Helper creating a dns.name_question"
        q = dns.name_question()
        q.name = name
        q.question_type = qtype
        q.question_class = qclass
        return q

    def get_dns_domain(self):
        "Helper to get dns domain"
        return os.getenv('REALM', 'example.com').lower()

    def test_one_a_query(self):
        "create a query packet containing one query record"
        p = self.make_name_packet(dns.DNS_OPCODE_QUERY)
        questions = []

        name = "%s.%s" % (os.getenv('DC_SERVER'), self.get_dns_domain())
        q = self.make_name_question(name, dns.DNS_QTYPE_A, dns.DNS_QCLASS_IN)
        print "asking for ", q.name
        questions.append(q)

        self.finish_name_packet(p, questions)
        response = self.dns_transaction_udp(p)
        self.assert_dns_rcode_equals(response, dns.DNS_RCODE_OK)
        self.assert_dns_opcode_equals(response, dns.DNS_OPCODE_QUERY)

    def test_two_queries(self):
        "create a query packet containing two query records"
        p = self.make_name_packet(dns.DNS_OPCODE_QUERY)
        questions = []

        name = "%s.%s" % (os.getenv('DC_SERVER'), self.get_dns_domain())
        q = self.make_name_question(name, dns.DNS_QTYPE_A, dns.DNS_QCLASS_IN)
        questions.append(q)

        name = "%s.%s" % ('bogusname', self.get_dns_domain())
        q = self.make_name_question(name, dns.DNS_QTYPE_A, dns.DNS_QCLASS_IN)
        questions.append(q)

        self.finish_name_packet(p, questions)
        response = self.dns_transaction_udp(p)
        self.assert_dns_rcode_equals(response, dns.DNS_RCODE_FORMERR)

    def dns_transaction_udp(self, packet, host=os.getenv('DC_SERVER_IP')):
        "send a DNS query and read the reply"
        s = None
        try:
            send_packet = ndr.ndr_pack(packet)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
            s.connect((host, 53))
            s.send(send_packet, 0)
            recv_packet = s.recv(2048, 0)
            return ndr.ndr_unpack(dns.name_packet, recv_packet)
        finally:
            if s is not None:
                s.close()

if __name__ == "__main__":
    import unittest
    unittest.main()