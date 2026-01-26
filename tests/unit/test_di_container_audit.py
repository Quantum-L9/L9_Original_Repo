"""
Unit Tests for DIContainer Audit Enhancements
==============================================

Tests the new methods added to DIContainer for Phase 0 Plan 3:
- get_optional() for optional dependency resolution
- list_registrations() for service inventory

Test Coverage:
- get_optional() returns instance when registered
- get_optional() returns None when not registered
- get_optional() returns None on resolution errors
- list_registrations() returns correct metadata
- list_registrations() shows lifecycle types
- list_registrations() shows instantiation status

Mutation Testing Target: 85%+ score
"""

from unittest.mock import Mock

from core.di.container import (
    DIContainer,
)


class TestGetOptional:
    """Test get_optional() method for optional dependency resolution."""

    def test_get_optional_returns_instance_when_registered(self):
        """Test get_optional() returns instance for registered service."""
        container = DIContainer()

        # Register a service
        mock_service = Mock()
        container.bind_singleton(Mock, lambda: mock_service)

        # Resolve optionally
        result = container.get_optional(Mock)

        assert result is mock_service

    def test_get_optional_returns_none_when_not_registered(self):
        """Test get_optional() returns None for unregistered service."""
        container = DIContainer()

        # Don't register anything
        result = container.get_optional(Mock)

        assert result is None

    def test_get_optional_returns_none_on_resolution_error(self):
        """Test get_optional() returns None when resolution fails."""
        container = DIContainer()

        # Register a service that will fail to resolve
        def failing_factory():
            raise RuntimeError("Factory failed")

        container.bind_singleton(Mock, failing_factory)

        # Should return None instead of raising
        result = container.get_optional(Mock)

        assert result is None

    def test_get_optional_singleton_caching(self):
        """Test get_optional() respects singleton caching."""
        container = DIContainer()

        call_count = [0]

        def factory():
            call_count[0] += 1
            return Mock()

        container.bind_singleton(Mock, factory)

        # First call
        result1 = container.get_optional(Mock)
        assert call_count[0] == 1

        # Second call should return cached instance
        result2 = container.get_optional(Mock)
        assert call_count[0] == 1  # Factory not called again
        assert result1 is result2

    def test_get_optional_transient_creates_new_instances(self):
        """Test get_optional() creates new instances for transient services."""
        container = DIContainer()

        call_count = [0]

        def factory():
            call_count[0] += 1
            return Mock()

        container.bind_transient(Mock, factory)

        # First call
        result1 = container.get_optional(Mock)
        assert call_count[0] == 1

        # Second call should create new instance
        result2 = container.get_optional(Mock)
        assert call_count[0] == 2  # Factory called again
        assert result1 is not result2


class TestListRegistrations:
    """Test list_registrations() method for service inventory."""

    def test_list_registrations_empty_container(self):
        """Test list_registrations() on empty container."""
        container = DIContainer()

        registrations = container.list_registrations()

        assert registrations == {}

    def test_list_registrations_singleton_not_instantiated(self):
        """Test list_registrations() shows singleton before instantiation."""
        container = DIContainer()

        class TestService:
            pass

        container.bind_singleton(TestService, lambda: TestService())

        registrations = container.list_registrations()

        assert "TestService" in registrations
        assert registrations["TestService"]["lifecycle"] == "singleton"
        assert registrations["TestService"]["instantiated"] is False
        assert "instance_type" not in registrations["TestService"]

    def test_list_registrations_singleton_after_instantiation(self):
        """Test list_registrations() shows singleton after instantiation."""
        container = DIContainer()

        class TestService:
            pass

        container.bind_singleton(TestService, lambda: TestService())

        # Instantiate
        container.resolve(TestService)

        registrations = container.list_registrations()

        assert "TestService" in registrations
        assert registrations["TestService"]["lifecycle"] == "singleton"
        assert registrations["TestService"]["instantiated"] is True
        assert registrations["TestService"]["instance_type"] == "TestService"

    def test_list_registrations_transient(self):
        """Test list_registrations() shows transient services."""
        container = DIContainer()

        class TestService:
            pass

        container.bind_transient(TestService, lambda: TestService())

        registrations = container.list_registrations()

        assert "TestService" in registrations
        assert registrations["TestService"]["lifecycle"] == "transient"
        assert registrations["TestService"]["instantiated"] is False

    def test_list_registrations_multiple_services(self):
        """Test list_registrations() with multiple services."""
        container = DIContainer()

        class ServiceA:
            pass

        class ServiceB:
            pass

        class ServiceC:
            pass

        container.bind_singleton(ServiceA, lambda: ServiceA())
        container.bind_transient(ServiceB, lambda: ServiceB())
        container.bind_singleton(ServiceC, lambda: ServiceC())

        # Instantiate only ServiceA
        container.resolve(ServiceA)

        registrations = container.list_registrations()

        assert len(registrations) == 3
        assert "ServiceA" in registrations
        assert "ServiceB" in registrations
        assert "ServiceC" in registrations

        # Check ServiceA is instantiated
        assert registrations["ServiceA"]["instantiated"] is True

        # Check ServiceB and ServiceC are not instantiated
        assert registrations["ServiceB"]["instantiated"] is False
        assert registrations["ServiceC"]["instantiated"] is False

    def test_list_registrations_metadata_structure(self):
        """Test list_registrations() returns correct metadata structure."""
        container = DIContainer()

        class TestService:
            pass

        container.bind_singleton(TestService, lambda: TestService())
        container.resolve(TestService)

        registrations = container.list_registrations()
        metadata = registrations["TestService"]

        # Check required fields
        assert "interface" in metadata
        assert "lifecycle" in metadata
        assert "instantiated" in metadata
        assert "instance_type" in metadata

        # Check values
        assert metadata["interface"] == "TestService"
        assert metadata["lifecycle"] == "singleton"
        assert metadata["instantiated"] is True
        assert metadata["instance_type"] == "TestService"

    def test_list_registrations_count_accuracy(self):
        """Test list_registrations() returns accurate count."""
        container = DIContainer()

        # Register 5 services
        for i in range(5):
            class_name = f"Service{i}"
            service_class = type(class_name, (), {})
            container.bind_singleton(service_class, lambda cls=service_class: cls())

        registrations = container.list_registrations()

        assert len(registrations) == 5


class TestDIContainerIntegration:
    """Integration tests for DIContainer with new methods."""

    def test_get_optional_with_dependencies(self):
        """Test get_optional() with service that has dependencies."""
        container = DIContainer()

        class DependencyA:
            pass

        class ServiceB:
            def __init__(self, dep_a: DependencyA):
                self.dep_a = dep_a

        # Register both
        container.bind_singleton(DependencyA, lambda: DependencyA())
        container.bind_singleton(ServiceB, ServiceB)

        # Resolve optionally
        result = container.get_optional(ServiceB)

        assert result is not None
        assert isinstance(result, ServiceB)
        assert isinstance(result.dep_a, DependencyA)

    def test_list_registrations_after_clear_singletons(self):
        """Test list_registrations() after clearing singletons."""
        container = DIContainer()

        class TestService:
            pass

        container.bind_singleton(TestService, lambda: TestService())
        container.resolve(TestService)

        # Clear singletons
        container.clear_singletons()

        registrations = container.list_registrations()

        # Binding still exists but not instantiated
        assert "TestService" in registrations
        assert registrations["TestService"]["instantiated"] is False


# =============================================================================
# Mutation Testing Targets
# =============================================================================


class TestMutationTargets:
    """
    Tests specifically designed to kill common mutations.
    """

    def test_get_optional_none_vs_false(self):
        """Kill mutation: return None -> return False."""
        container = DIContainer()

        result = container.get_optional(Mock)

        assert result is None
        assert result is not False

    def test_list_registrations_empty_dict_vs_none(self):
        """Kill mutation: return {} -> return None."""
        container = DIContainer()

        result = container.list_registrations()

        assert result == {}
        assert result is not None

    def test_instantiated_true_vs_false(self):
        """Kill mutation: instantiated = True -> instantiated = False."""
        container = DIContainer()

        class TestService:
            pass

        container.bind_singleton(TestService, lambda: TestService())

        # Before instantiation
        regs1 = container.list_registrations()
        assert regs1["TestService"]["instantiated"] is False

        # After instantiation
        container.resolve(TestService)
        regs2 = container.list_registrations()
        assert regs2["TestService"]["instantiated"] is True

    def test_lifecycle_singleton_vs_transient(self):
        """Kill mutation: 'singleton' -> 'transient'."""
        container = DIContainer()

        class SingletonService:
            pass

        class TransientService:
            pass

        container.bind_singleton(SingletonService, lambda: SingletonService())
        container.bind_transient(TransientService, lambda: TransientService())

        regs = container.list_registrations()

        assert regs["SingletonService"]["lifecycle"] == "singleton"
        assert regs["TransientService"]["lifecycle"] == "transient"

    def test_get_optional_catches_binding_not_found_error(self):
        """Kill mutation: except BindingNotFoundError -> except Exception."""
        container = DIContainer()

        # Should catch BindingNotFoundError specifically
        result = container.get_optional(Mock)

        assert result is None

    def test_list_registrations_count_exact(self):
        """Kill mutation: len(registrations) >= 3 -> len(registrations) > 3."""
        container = DIContainer()

        class Service1:
            pass

        class Service2:
            pass

        class Service3:
            pass

        container.bind_singleton(Service1, lambda: Service1())
        container.bind_singleton(Service2, lambda: Service2())
        container.bind_singleton(Service3, lambda: Service3())

        regs = container.list_registrations()

        assert len(regs) == 3  # Exact match
