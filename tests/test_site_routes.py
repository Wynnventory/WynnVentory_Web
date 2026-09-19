"""Tests for the /site/* JSON routes the website's JavaScript fetches.

They sit on the web blueprint and call the service layer directly, like the
server-rendered pages; they are not part of the public API.
"""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from flask import Flask

from modules.routes.api.wynncraft_api import UpstreamError
from modules.routes.web.web import web_bp


def make_test_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(web_bp)
    return app


class TestSiteRoutes(unittest.TestCase):
    def setUp(self):
        self.client = make_test_app().test_client()

    # --- history ---------------------------------------------------------
    def test_history_returns_the_points_as_json(self):
        points = [{'timestamp': '2026-09-17T00:00:00Z', 'average_price': 100.0}]
        with patch('modules.services.market_service.get_history', return_value=points) as get_history:
            resp = self.client.get('/site/history/Slayer?start_date=2026-09-10&end_date=2026-09-17&tier=2&shiny=true')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), points)
        get_history.assert_called_once_with(
            item_name='Slayer', shiny=True, tier=2,
            start_date=datetime(2026, 9, 10), end_date=datetime(2026, 9, 17))

    def test_history_defaults_when_no_params_are_given(self):
        with patch('modules.services.market_service.get_history', return_value=[]) as get_history:
            resp = self.client.get('/site/history/Slayer')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), [])
        get_history.assert_called_once_with(
            item_name='Slayer', shiny=False, tier=None, start_date=None, end_date=None)

    def test_history_rejects_a_bad_tier(self):
        resp = self.client.get('/site/history/Slayer?tier=abc')
        self.assertEqual(resp.status_code, 400)

    def test_history_rejects_a_bad_date(self):
        resp = self.client.get('/site/history/Slayer?start_date=yesterday')
        self.assertEqual(resp.status_code, 400)

    # --- ranking ---------------------------------------------------------
    def test_ranking_returns_every_row_in_one_response(self):
        rows = [{'rank': i, 'name': f'Item{i}', 'itemType': 'Weapon'} for i in range(1, 301)]
        with patch('modules.services.market_service.get_ranking', return_value=rows) as get_ranking:
            resp = self.client.get('/site/ranking?start_date=2026-09-10&end_date=2026-09-17')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.get_json()), 300)
        get_ranking.assert_called_once_with(
            start_date=datetime(2026, 9, 10), end_date=datetime(2026, 9, 17))

    def test_ranking_rejects_a_bad_date(self):
        resp = self.client.get('/site/ranking?end_date=nope')
        self.assertEqual(resp.status_code, 400)

    # --- item tooltip ----------------------------------------------------
    def test_item_returns_the_item(self):
        with patch('modules.services.item_service.fetch_item', return_value={'name': 'Slayer'}):
            resp = self.client.get('/site/item/Slayer')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {'name': 'Slayer'})

    def test_unknown_item_is_404(self):
        with patch('modules.services.item_service.fetch_item', return_value=None):
            resp = self.client.get('/site/item/Nope')
        self.assertEqual(resp.status_code, 404)

    def test_unsupported_item_type_is_404(self):
        with patch('modules.services.item_service.fetch_item', side_effect=ValueError('unsupported')):
            resp = self.client.get('/site/item/Weird')
        self.assertEqual(resp.status_code, 404)

    def test_item_upstream_outage_is_502(self):
        with patch('modules.services.item_service.fetch_item', side_effect=UpstreamError('down')):
            resp = self.client.get('/site/item/Slayer')
        self.assertEqual(resp.status_code, 502)

    # --- aspect tooltip --------------------------------------------------
    def test_aspect_returns_the_aspect(self):
        with patch('modules.services.aspect_service.fetch_aspect', return_value={'name': 'Aspect of X'}) as fetch:
            resp = self.client.get('/site/aspect/archer/Aspect%20of%20X')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {'name': 'Aspect of X'})
        fetch.assert_called_once_with('archer', 'Aspect of X')

    def test_unknown_aspect_is_404(self):
        with patch('modules.services.aspect_service.fetch_aspect', return_value=None):
            resp = self.client.get('/site/aspect/archer/Nope')
        self.assertEqual(resp.status_code, 404)

    def test_aspect_upstream_outage_is_502(self):
        with patch('modules.services.aspect_service.fetch_aspect', side_effect=UpstreamError('down')):
            resp = self.client.get('/site/aspect/archer/Aspect%20of%20X')
        self.assertEqual(resp.status_code, 502)


if __name__ == '__main__':
    unittest.main()
