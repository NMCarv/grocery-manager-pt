"""Testes para scripts/config.py — fonte única de configuração de mercados."""
import pytest
import config

class TestOnlineMarketEnum:
    def test_continente_value(self):
        assert config.OnlineMarket.CONTINENTE == "continente"

    def test_pingodoce_value(self):
        assert config.OnlineMarket.PINGODOCE == "pingodoce"

    def test_enum_values_are_strings(self):
        """str, Enum — cada membro pode ser usado directamente como string."""
        for market in config.OnlineMarket:
            assert isinstance(market, str)

    def test_string_equality(self):
        """Comparação directa com strings literais funciona sem .value."""
        assert config.OnlineMarket.CONTINENTE == "continente"
        assert "continente" == config.OnlineMarket.CONTINENTE

    def test_all_markets_covered_in_delivery_config(self):
        """Cada mercado no enum tem entrada correspondente no DELIVERY_CONFIG."""
        for market in config.OnlineMarket:
            assert market.value in config.DELIVERY_CONFIG, (
                f"Mercado '{market.value}' em falta no DELIVERY_CONFIG"
            )

    def test_no_orphan_delivery_config_entries(self):
        """DELIVERY_CONFIG não tem entradas para mercados não definidos no enum."""
        market_values = {m.value for m in config.OnlineMarket}
        for key in config.DELIVERY_CONFIG:
            assert key in market_values, (
                f"DELIVERY_CONFIG tem entrada '{key}' sem correspondência no enum"
            )


class TestOnlineMarketIDs:
    def test_contains_all_enum_values(self):
        for market in config.OnlineMarket:
            assert market.value in config.ONLINE_MARKET_IDS

    def test_is_frozenset(self):
        assert isinstance(config.ONLINE_MARKET_IDS, frozenset)

    def test_string_membership(self):
        """Strings simples podem ser testadas contra ONLINE_MARKET_IDS."""
        assert "continente" in config.ONLINE_MARKET_IDS
        assert "pingodoce" in config.ONLINE_MARKET_IDS
        assert "lidl" not in config.ONLINE_MARKET_IDS
        assert "makro" not in config.ONLINE_MARKET_IDS
        assert None not in config.ONLINE_MARKET_IDS

    def test_size_matches_enum(self):
        assert len(config.ONLINE_MARKET_IDS) == len(config.OnlineMarket)


class TestMarketsList:
    def test_is_list(self):
        assert isinstance(config.MARKETS, list)

    def test_contains_all_markets(self):
        for market in config.OnlineMarket:
            assert market.value in config.MARKETS

    def test_size_matches_enum(self):
        assert len(config.MARKETS) == len(config.OnlineMarket)

    def test_consistent_with_online_market_ids(self):
        assert set(config.MARKETS) == config.ONLINE_MARKET_IDS


class TestDeliveryConfig:
    def test_continente_has_required_fields(self):
        cfg = config.DELIVERY_CONFIG["continente"]
        assert "cost" in cfg
        assert "free_threshold" in cfg
        assert "min_order" in cfg

    def test_pingodoce_has_required_fields(self):
        cfg = config.DELIVERY_CONFIG["pingodoce"]
        assert "cost" in cfg
        assert "free_threshold" in cfg
        assert "min_order" in cfg

    def test_cost_is_positive(self):
        for market, cfg in config.DELIVERY_CONFIG.items():
            assert cfg["cost"] >= 0, f"{market}: cost deve ser >= 0"

    def test_free_threshold_above_cost(self):
        """Threshold de entrega grátis deve ser maior que o custo de entrega."""
        for market, cfg in config.DELIVERY_CONFIG.items():
            assert cfg["free_threshold"] > cfg["cost"], (
                f"{market}: free_threshold deve ser > cost"
            )


class TestCacheTTL:
    def test_cache_ttl_is_positive_int(self):
        assert isinstance(config.CACHE_TTL_HOURS, int)
        assert config.CACHE_TTL_HOURS > 0
