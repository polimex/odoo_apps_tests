from odoo import fields
from odoo.tests import common
from .common import create_webstacks, create_acc_grs_cnt, create_contacts, create_card, \
    get_ws_doors


class ZoneTests(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(ZoneTests, cls).setUpClass()
        cls._ws = create_webstacks(cls.env, webstacks=1, controllers=[2, 2])
        cls._doors = get_ws_doors(cls._ws)
        cls._acc_grs = create_acc_grs_cnt(cls.env, 1)

        cls._contacts = create_contacts(cls.env, ['Greg', 'Cooler Greg', 'Richard'])

        cls._cards = cls.env['hr.rfid.card']
        cls._cards += create_card(cls.env, '0000000001', cls._contacts[0])
        cls._cards += create_card(cls.env, '0000000002', cls._contacts[1])
        cls._cards += create_card(cls.env, '0000000003', cls._contacts[2])

        cls._contacts[0].add_acc_gr(cls._acc_grs[0])
        cls._contacts[1].add_acc_gr(cls._acc_grs[0])
        cls._contacts[2].add_acc_gr(cls._acc_grs[0])

        cls._acc_grs[0].add_doors(cls._doors[0], cls._def_ts)

        cls._zone = cls.env['hr.rfid.zone'].create({ 'name': 'asd' })
        cls._zone.door_ids = cls._doors

    def test_person_went_through(self):
        ev_env = self.env['hr.rfid.event.user']
        contact = self._contacts[0]
        door = self._doors[0]
        zone = self._zone

        ev = ev_env.create({
            'ctrl_addr': 1,
            'contact_id': contact.id,
            'door_id': door.id,
            'reader_id': door.reader_ids[0].id,
            'card_id': contact.hr_rfid_card_ids[0].id,
            'event_time': fields.datetime.now().strftime('%m.%d.%y %H:%M:%S'),
            'event_action': '1',
        })

        zone.contact_ids = self.env['res.partner']
        self.assertFalse(zone.employee_ids)

        zone.person_went_through(ev)
        self.assertEqual(zone.contact_ids, contact)
        self.assertFalse(zone.employee_ids)

        zone.person_went_through(ev)
        self.assertFalse(zone.contact_ids)
        self.assertFalse(zone.employee_ids)

        zone.person_went_through(ev)
        self.assertEqual(zone.contact_ids, contact)
        self.assertFalse(zone.employee_ids)

        zone.person_went_through(ev)
        self.assertFalse(zone.contact_ids)
        self.assertFalse(zone.employee_ids)

    def test_person_entered(self):
        contact = self._contacts[0]
        zone = self._zone

        self.assertFalse(zone.contact_ids)
        self.assertFalse(zone.employee_ids)

        zone.person_entered(contact, [])
        self.assertEqual(zone.contact_ids, contact)
        self.assertFalse(zone.employee_ids)

        zone.person_entered(contact, [])
        self.assertEqual(zone.contact_ids, contact)
        self.assertFalse(zone.employee_ids)

    def test_person_left(self):
        contact = self._contacts[0]
        zone = self._zone

        self.assertFalse(zone.contact_ids)
        self.assertFalse(zone.employee_ids)

        zone.contact_ids = contact
        zone.person_left(contact, [])
        self.assertFalse(zone.contact_ids)
        self.assertFalse(zone.employee_ids)

        zone.person_left(contact, [])
        self.assertFalse(zone.contact_ids)
        self.assertFalse(zone.employee_ids)
