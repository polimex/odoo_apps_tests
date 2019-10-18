from odoo.tests import common
from odoo import exceptions
from .common import create_webstacks, create_acc_grs_cnt, create_contacts, create_card, get_ws_doors
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from queue import Queue
from functools import partial, reduce

import json


class WebstackEmulationHandler(BaseHTTPRequestHandler):
    def __init__(self, queue: Queue, *args, **kwargs):
        self._q = queue
        super().__init__(*args, **kwargs)

    def do_GET(self):
        body = {
            'bridgeClient': {
                'add_info': 0,
                'auto_connect': 0,
                'last_error': 0,
                'port': 5000,
                'status': 0,
                'url': 'url.or.ip.com'
            },
            'convertor': 449156,
            'currentIPFiltering': {
                'IP1': '0.0.0.0',
                'checkbox_Enable_IP1_filter': ''
            },
            'inputOutputHardware': {
                'portInDigital': 5,
                'portOut': 4,
                'uarts': [
                    [
                        0,
                        [
                            0,
                            2,
                            5
                        ]
                    ],
                    [
                        2,
                        [
                            0,
                            1,
                            2,
                            5
                        ]
                    ]
                ]
            },
            'netConfig': {
                'Gateway': '192.168.74.254',
                'Host_Name': 'WIFI-16C4',
                'IP_Address': '192.168.74.61',
                'MAC_Address': '24:0a:c4:16:04:c3',
                'Primary_DNS': '192.168.74.254',
                'Secondary_DNS': '0.0.0.0',
                'Subnet_Mask': '255.255.255.0',
                'checkbox_DHCP': 'checked',
                'net_mode': 1,
                'sntp_server': 'bg.pool.ntp.org'
            },
            'sdk': {
                'ConnectionType': 3,
                'TCPStackVersion': 'v3.3-71-g46b12a5',
                'devFound': 1,
                'deviceTime': 1571388442,
                'freeRAM': 69716,
                'heartBeatCounter': 2375,
                'heartBeatTimeOut': 11,
                'isBridgeActive': 0,
                'isCmdExecute': 0,
                'isCmdWaiting': 0,
                'isDeviceScan': 0,
                'isEventPause': 0,
                'isEventScan': 1,
                'isServerToSendDown': 0,
                'maxDevInList': 64,
                'remoteIP': '0.0.0.0',
                'scanIDfrom': 0,
                'scanIDprogress': 0,
                'scanIDto': 254,
                'sdkHardware': '100.1',
                'sdkVersion': '1.46',
                'upTime': '1d 15:51:08'
            },
            'sdkSettings': {
                'Bridge_PORT': 5000,
                'HeartBeat_Time': 60,
                'Server_PORT': '8069',
                'Server_URL': 'ilian.com/hr/rfid/event',
                'checkbox_Enable_HTTP_IO_Event_Server_Push': '',
                'checkbox_Enable_HTTP_Pull_Technology': 'checked',
                'checkbox_Enable_HTTP_Server_Push': 'checked',
                'checkbox_Enable_HeartBeat': 'checked',
                'checkbox_Enable_TCP_Bridge': 'checked',
                'checkbox_Enable_custom_Bridge_port': '',
                'checkbox_SDK_Password_Require': '',
                'enable_odoo': 1,
                'enable_tls': 0,
                'modbus_id': 239,
                'modbus_port': 502,
                'modbus_uart_timeout': 1000,
                'rbridge_started': 0
            },
            'uartConfig': [
                {
                    'br': 9600,
                    'db': 3,
                    'fc': 0,
                    'ft': 122,
                    'port': 0,
                    'pr': 0,
                    'rt': False,
                    'sb': 1,
                    'usage': 0
                },
                {
                    'br': 9600,
                    'db': 3,
                    'fc': 0,
                    'ft': 122,
                    'port': 2,
                    'pr': 0,
                    'rt': False,
                    'sb': 1,
                    'usage': 1
                }
            ],
            'wifiConfig': {
                'apauth': 3,
                'apbeac': 100,
                'apchan': 11,
                'aphidd': 0,
                'apmac': '00:24:fe:3f:00:00',
                'apmaxc': 4,
                'apssid': 'WIFI-16C4',
                'chan': 0,
                'mode': 1,
                'phy': 5,
                'rssi': 0,
                'ssid': 'PH',
                'stamac': '24:0a:c4:16:04:c0',
                'status': 1073610744
            }
        }
        body = json.dumps(body)
        self.send_response(200)
        self.send_header('content-length', len(body))
        self.end_headers()
        self.wfile.write(body.encode())

    def do_POST(self):
        buff = self.rfile.read(int(self.headers['content-length'])).decode()
        self._q.put(buff)
        self.send_response(200)
        self.end_headers()


class HttpServerThread(Thread):
    def __init__(self, server: HTTPServer):
        super().__init__()
        self._server = server

    def run(self):
        self._server.serve_forever()


class WebstackTests(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(WebstackTests, cls).setUpClass()
        cls._ws = create_webstacks(cls.env, 1, [2])

    def run_test_webstack_server(self):
        queue = Queue()
        self._q = queue
        custom_handler = partial(WebstackEmulationHandler, queue)
        self._ws_server = HTTPServer(('', 80), custom_handler)
        self._ws_server_thread = HttpServerThread(self._ws_server)
        self._ws_server_thread.start()

    def stop_test_webstack_server(self):
        self._ws_server.shutdown()
        self._ws_server_thread.join()
        self._ws_server = None
        self._ws_server_thread = None

    def test_action_set_webstack_settings(self):
        self._ws.last_ip = 'localhost'

        with self.assertRaises(exceptions.ValidationError):
            self._ws.action_set_webstack_settings()

        self.run_test_webstack_server()

        try:
            self._ws.action_set_webstack_settings()
        except exceptions.ValidationError:
            self.fail(msg="action_set_webstack_settings failed when it shouldn't have")

        self.stop_test_webstack_server()

        self.assertEqual(self._q.qsize(), 2)

        msg = self._q.get()

        try:
            js_uart_conf = json.loads(msg)
        except json.decoder.JSONDecodeError as e:
            self.fail('Could not load js_uart_conf, even though we should have been able to. Error: ' + e.msg)

        self.assertEqual(type(js_uart_conf), type([]))
        self.assertEqual(len(js_uart_conf), 2)

        js1 = js_uart_conf[0]
        js2 = js_uart_conf[1]

        self.assertIn('br', js1)
        self.assertIn('db', js1)
        self.assertIn('fc', js1)
        self.assertIn('ft', js1)
        self.assertIn('port', js1)
        self.assertIn('pr', js1)
        self.assertIn('rt', js1)
        self.assertIn('sb', js1)
        self.assertIn('usage', js1)
        self.assertEqual(js1['br'], 9600)
        self.assertEqual(js1['db'], 3)
        self.assertEqual(js1['fc'], 0)
        self.assertEqual(js1['ft'], 122)
        self.assertEqual(js1['port'], 0)
        self.assertEqual(js1['pr'], 0)
        self.assertEqual(js1['rt'], False)
        self.assertEqual(js1['sb'], 1)
        self.assertEqual(js1['usage'], 0)
        self.assertIn('br', js2)
        self.assertIn('db', js2)
        self.assertIn('fc', js2)
        self.assertIn('ft', js2)
        self.assertIn('port', js2)
        self.assertIn('pr', js2)
        self.assertIn('rt', js2)
        self.assertIn('sb', js2)
        self.assertIn('usage', js2)
        self.assertEqual(type(js1['br']), type(0))
        self.assertEqual(type(js1['db']), type(0))
        self.assertEqual(type(js1['fc']), type(0))
        self.assertEqual(type(js1['ft']), type(0))
        self.assertEqual(type(js1['port']), type(0))
        self.assertEqual(type(js1['pr']), type(0))
        self.assertEqual(type(js1['rt']), type(False))
        self.assertEqual(type(js1['sb']), type(0))
        self.assertEqual(type(js1['usage']), type(0))

        msg = self._q.get()
        odoo_url = str(self.env['ir.config_parameter'].get_param('web.base.url'))
        splits = odoo_url.split(':')
        odoo_url = splits[1][2:]
        if len(splits) == 3:
            odoo_port = int(splits[2], 10)
        else:
            odoo_port = 80
        odoo_url += '/hr/rfid/event'

        params = str(msg).split('&')
        self.assertEqual(len(params), 9)
        self.assertIn('sdk=1', params)
        self.assertIn('stsd=1', params)
        self.assertIn('sdts=1', params)
        self.assertIn('stsu=' + odoo_url, params)
        self.assertIn('prt=' + str(odoo_port), params)
        self.assertIn('hb=1', params)
        self.assertIn('thb=60', params)
        self.assertIn('odoo=1', params)

    def test_action_check_if_ws_available(self):
        # TODO Check if it will throw an error if we send it bad data
        self._ws.last_ip = 'localhost'

        with self.assertRaises(exceptions.ValidationError):
            self._ws.action_check_if_ws_available()

        self.run_test_webstack_server()

        try:
            self._ws.action_check_if_ws_available()
        except exceptions.ValidationError:
            self.fail(msg="action_check_if_ws_available failed when it shouldn't have")

        self.stop_test_webstack_server()

        self.assertEqual(self._q.qsize(), 0)

    def test_action_set_active_inactive(self):
        self._ws.action_set_active()
        self.assertTrue(self._ws.ws_active)
        self._ws.action_set_active()
        self.assertTrue(self._ws.ws_active)
        self._ws.action_set_inactive()
        self.assertFalse(self._ws.ws_active)
        self._ws.action_set_inactive()
        self.assertFalse(self._ws.ws_active)
        self._ws.action_set_active()
        self.assertTrue(self._ws.ws_active)


class ControllerTests(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(ControllerTests, cls).setUpClass()
        cls._ws = create_webstacks(cls.env, 1, [2])
        cls._controllers = cls._ws.controllers
        cls._doors = get_ws_doors(cls._ws)
        cls._acc_grs = create_acc_grs_cnt(cls.env, 2)
        cls._contacts = create_contacts(cls.env, [ 'Josh', 'Uncool Josh', 'Reaver Spolarity' ])

        cls._cards = cls.env['hr.rfid.card']
        cls._cards += create_card(cls.env, '0000000001', cls._contacts[0])
        cls._cards += create_card(cls.env, '0000000002', cls._contacts[1])
        cls._cards += create_card(cls.env, '0000000003', cls._contacts[1])

        cls._contacts[0].add_acc_gr(cls._acc_grs[0])
        cls._contacts[1].add_acc_gr(cls._acc_grs[0])
        cls._contacts[1].add_acc_gr(cls._acc_grs[1])
        cls._contacts[2].add_acc_gr(cls._acc_grs[0])
        cls._contacts[2].add_acc_gr(cls._acc_grs[1])

        cls._def_ts = cls.env.ref('hr_rfid.hr_rfid_time_schedule_0')

        cls._acc_grs[0].add_doors(cls._doors[0], cls._def_ts)
        cls._acc_grs[1].add_doors(cls._doors[1], cls._def_ts)

    def test_button_reload_cards(self):
        rels_env = self.env['hr.rfid.card.door.rel']
        rels_env.search([]).unlink()

        self._controllers[0].button_reload_cards()
        rels = rels_env.search([])

        self.assertEqual(len(rels), 5)

        expected_rels = [
            (self._cards[0], self._doors[0], self._def_ts),
            (self._cards[1], self._doors[0], self._def_ts),
            (self._cards[1], self._doors[1], self._def_ts),
            (self._cards[2], self._doors[0], self._def_ts),
            (self._cards[2], self._doors[1], self._def_ts),
        ]
        rels = [ (a.card_id, a.door_id, a.time_schedule_id) for a in rels ]
        self.assertCountEqual(expected_rels, rels)

        rels_env.search([]).unlink()
        self.env['hr.rfid.access.group'].search([]).unlink()

        self._controllers[0].button_reload_cards()
        rels = rels_env.search([])
        self.assertFalse(rels.exists())

    def test_change_io_table(self):
        ctrl = self._controllers[0]
        cmds_env = self.env['hr.rfid.command']
        cmds_env.search([]).unlink()

        def_io_table = ctrl.get_default_io_table(ctrl.hw_version, ctrl.sw_version, ctrl.mode)
        ctrl.io_table = def_io_table
        new_io_table = def_io_table[0] + str(9 - int(def_io_table[0])) + def_io_table[2:]

        ctrl.change_io_table(new_io_table)

        cmd = cmds_env.search([])
        self.assertEqual(len(cmd), 1)
        self.assertEqual(cmd.webstack_id, ctrl.webstack_id)
        self.assertEqual(cmd.controller_id, ctrl)
        self.assertEqual(cmd.cmd, 'D9')
        self.assertEqual(cmd.cmd_data, '00' + new_io_table)

        cmds_env.search([]).unlink()

        ctrl.change_io_table(ctrl.io_table)
        cmd = cmds_env.search([])
        self.assertFalse(cmd.exists())

    def test_io_table_wizard(self):
        ctrl = self._controllers[0]
        ctrl.io_table = ctrl.get_default_io_table(ctrl.hw_version, ctrl.sw_version, ctrl.mode)
        wiz = self.env['hr.rfid.ctrl.io.table.wiz'].with_context(active_ids=ctrl.id).create({})

        wiz_io_table = ''
        for row in wiz.io_row_ids:
            outs = [ row.out8, row.out7, row.out6, row.out5, row.out4, row.out3, row.out2, row.out1 ]
            row_str = ''.join([ '%02X' % a for a in outs ])
            wiz_io_table += row_str

        self.assertEqual(ctrl.io_table, wiz_io_table)

        wiz.io_row_ids[0].out5 = 9 - wiz.io_row_ids[0].out5
        wiz.io_row_ids[1].out5 = 9 - wiz.io_row_ids[1].out5
        wiz.io_row_ids[2].out5 = 9 - wiz.io_row_ids[2].out5
        wiz.io_row_ids[3].out5 = 9 - wiz.io_row_ids[3].out5
        wiz.io_row_ids[4].out5 = 9 - wiz.io_row_ids[4].out5
        wiz.io_row_ids[5].out5 = 9 - wiz.io_row_ids[5].out5

        new_io_table = ''
        for row in wiz.io_row_ids:
            outs = [ row.out8, row.out7, row.out6, row.out5, row.out4, row.out3, row.out2, row.out1 ]
            row_str = ''.join([ '%02X' % a for a in outs ])
            new_io_table += row_str

        wiz.save_table()
        self.assertEqual(new_io_table, ctrl.io_table)


class DoorTests(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(DoorTests, cls).setUpClass()
        cls._ws = create_webstacks(cls.env, 1, [2])
        cls._controllers = cls._ws.controllers
        cls._doors = get_ws_doors(cls._ws)
        cls._acc_grs = create_acc_grs_cnt(cls.env, 2)
        cls._contacts = create_contacts(cls.env, [ 'Josh', 'Uncool Josh', 'Reaver Spolarity' ])

        cls._cards = cls.env['hr.rfid.card']
        cls._cards += create_card(cls.env, '0000000001', cls._contacts[0])
        cls._cards += create_card(cls.env, '0000000002', cls._contacts[1])
        cls._cards += create_card(cls.env, '0000000003', cls._contacts[1])

        cls._contacts[0].add_acc_gr(cls._acc_grs[0])
        cls._contacts[1].add_acc_gr(cls._acc_grs[0])
        cls._contacts[1].add_acc_gr(cls._acc_grs[1])
        cls._contacts[2].add_acc_gr(cls._acc_grs[0])
        cls._contacts[2].add_acc_gr(cls._acc_grs[1])

        cls._def_ts = cls.env.ref('hr_rfid.hr_rfid_time_schedule_0')

        cls._acc_grs[0].add_doors(cls._doors[0], cls._def_ts)
        cls._acc_grs[1].add_doors(cls._doors[1], cls._def_ts)

    def run_test_webstack_server(self):
        queue = Queue()
        self._q = queue
        custom_handler = partial(WebstackEmulationHandler, queue)
        self._ws_server = HTTPServer(('', 80), custom_handler)
        self._ws_server_thread = HttpServerThread(self._ws_server)
        self._ws_server_thread.start()

    def stop_test_webstack_server(self):
        self._ws_server.shutdown()
        self._ws_server_thread.join()
        self._ws_server = None
        self._ws_server_thread = None

    def test_get_potential_cards(self):
        door = self._doors[0]

        cards = door.get_potential_cards()
        expected_cards = [
            (self._cards[0], self._def_ts),
            (self._cards[1], self._def_ts),
            (self._cards[2], self._def_ts),
        ]
        self.assertEqual(cards, expected_cards)

        self._contacts[0].remove_acc_gr(self._acc_grs[0])

        cards = door.get_potential_cards()
        expected_cards = [
            (self._cards[1], self._def_ts),
            (self._cards[2], self._def_ts),
        ]
        self.assertEqual(cards, expected_cards)

        self._contacts[1].remove_acc_gr(self._acc_grs[0])

        cards = door.get_potential_cards()
        self.assertEqual(len(cards), 0)

    def test_open_close_door(self):
        pass
