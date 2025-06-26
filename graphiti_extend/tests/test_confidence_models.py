"""
Tests for confidence models and data structures.
"""

import pytest
from datetime import datetime
from graphiti_extend.confidence.models import (
    OriginType,
    ConfidenceTrigger,
    ConfidenceHistory,
    ConfidenceUpdate,
    ConfidenceConfig
)


class TestOriginType:
    """Test OriginType enum."""
    
    def test_origin_type_values(self):
        """Test that all origin types have correct values."""
        assert OriginType.USER_GIVEN == "user_given"
        assert OriginType.INFERRED == "inferred"
        assert OriginType.SYSTEM_SUGGESTED == "system_suggested"
    
    def test_origin_type_membership(self):
        """Test that origin types are valid enum members."""
        assert "user_given" in [e.value for e in OriginType]
        assert "inferred" in [e.value for e in OriginType]
        assert "system_suggested" in [e.value for e in OriginType]
        assert "invalid" not in [e.value for e in OriginType]


class TestConfidenceTrigger:
    """Test ConfidenceTrigger enum."""
    
    def test_trigger_values(self):
        """Test that all triggers have correct values."""
        # User validation triggers
        assert ConfidenceTrigger.USER_REAFFIRMATION == "user_reaffirmation"
        assert ConfidenceTrigger.USER_REFERENCE == "user_reference"
        assert ConfidenceTrigger.USER_REASONING == "user_reasoning"
        assert ConfidenceTrigger.USER_CORRECTION == "user_correction"
        assert ConfidenceTrigger.USER_UNCERTAINTY == "user_uncertainty"
        
        # Network reinforcement triggers
        assert ConfidenceTrigger.NETWORK_SUPPORT == "network_support"
        assert ConfidenceTrigger.REASONING_USAGE == "reasoning_usage"
        assert ConfidenceTrigger.STRUCTURAL_SUPPORT == "structural_support"
        assert ConfidenceTrigger.INDIRECT_SUPPORT == "indirect_support"
        
        # System validation triggers
        assert ConfidenceTrigger.CONSISTENCY_CHECK == "consistency_check"
        assert ConfidenceTrigger.EXTERNAL_CORROBORATION == "external_corroboration"
        
        # Contradiction triggers
        assert ConfidenceTrigger.CONTRADICTION_DETECTED == "contradiction_detected"
        assert ConfidenceTrigger.REPEATED_CONTRADICTION == "repeated_contradiction"
        assert ConfidenceTrigger.CONTRADICTION_RESOLUTION == "contradiction_resolution"
        
        # Temporal triggers
        assert ConfidenceTrigger.DORMANCY_DECAY == "dormancy_decay"
        assert ConfidenceTrigger.EXTENDED_DORMANCY == "extended_dormancy"
        assert ConfidenceTrigger.ORPHANED_ENTITY == "orphaned_entity"
        
        # Initial assignment
        assert ConfidenceTrigger.INITIAL_ASSIGNMENT == "initial_assignment"
        assert ConfidenceTrigger.DUPLICATE_FOUND == "duplicate_found"
    
    def test_trigger_categories(self):
        """Test that triggers are properly categorized."""
        user_triggers = [
            ConfidenceTrigger.USER_REAFFIRMATION,
            ConfidenceTrigger.USER_REFERENCE,
            ConfidenceTrigger.USER_REASONING,
            ConfidenceTrigger.USER_CORRECTION,
            ConfidenceTrigger.USER_UNCERTAINTY
        ]
        
        network_triggers = [
            ConfidenceTrigger.NETWORK_SUPPORT,
            ConfidenceTrigger.REASONING_USAGE,
            ConfidenceTrigger.STRUCTURAL_SUPPORT,
            ConfidenceTrigger.INDIRECT_SUPPORT
        ]
        
        contradiction_triggers = [
            ConfidenceTrigger.CONTRADICTION_DETECTED,
            ConfidenceTrigger.REPEATED_CONTRADICTION,
            ConfidenceTrigger.CONTRADICTION_RESOLUTION
        ]
        
        temporal_triggers = [
            ConfidenceTrigger.DORMANCY_DECAY,
            ConfidenceTrigger.EXTENDED_DORMANCY,
            ConfidenceTrigger.ORPHANED_ENTITY
        ]
        
        # Verify all triggers are in expected categories
        all_triggers = set(ConfidenceTrigger)
        categorized_triggers = set(user_triggers + network_triggers + contradiction_triggers + temporal_triggers)
        categorized_triggers.add(ConfidenceTrigger.CONSISTENCY_CHECK)
        categorized_triggers.add(ConfidenceTrigger.EXTERNAL_CORROBORATION)
        categorized_triggers.add(ConfidenceTrigger.INITIAL_ASSIGNMENT)
        categorized_triggers.add(ConfidenceTrigger.DUPLICATE_FOUND)
        
        assert all_triggers == categorized_triggers


class TestConfidenceHistory:
    """Test ConfidenceHistory model."""
    
    def test_confidence_history_creation(self):
        """Test creating a confidence history entry."""
        timestamp = datetime.now()
        history = ConfidenceHistory(
            timestamp=timestamp,
            value=0.8,
            trigger=ConfidenceTrigger.USER_REAFFIRMATION,
            reason="User reaffirmed information",
            metadata={"context": "test"}
        )
        
        assert history.timestamp == timestamp
        assert history.value == 0.8
        assert history.trigger == ConfidenceTrigger.USER_REAFFIRMATION
        assert history.reason == "User reaffirmed information"
        assert history.metadata == {"context": "test"}
    
    def test_confidence_history_validation(self):
        """Test confidence value validation."""
        # Valid values
        ConfidenceHistory(
            timestamp=datetime.now(),
            value=0.0,
            trigger=ConfidenceTrigger.INITIAL_ASSIGNMENT,
            reason="Test"
        )
        
        ConfidenceHistory(
            timestamp=datetime.now(),
            value=1.0,
            trigger=ConfidenceTrigger.INITIAL_ASSIGNMENT,
            reason="Test"
        )
        
        ConfidenceHistory(
            timestamp=datetime.now(),
            value=0.5,
            trigger=ConfidenceTrigger.INITIAL_ASSIGNMENT,
            reason="Test"
        )
        
        # Invalid values should raise validation error
        with pytest.raises(ValueError):
            ConfidenceHistory(
                timestamp=datetime.now(),
                value=1.1,  # Above maximum
                trigger=ConfidenceTrigger.INITIAL_ASSIGNMENT,
                reason="Test"
            )
        
        with pytest.raises(ValueError):
            ConfidenceHistory(
                timestamp=datetime.now(),
                value=-0.1,  # Below minimum
                trigger=ConfidenceTrigger.INITIAL_ASSIGNMENT,
                reason="Test"
            )
    
    def test_confidence_history_optional_metadata(self):
        """Test that metadata is optional."""
        history = ConfidenceHistory(
            timestamp=datetime.now(),
            value=0.8,
            trigger=ConfidenceTrigger.USER_REAFFIRMATION,
            reason="Test"
        )
        
        assert history.metadata is None


class TestConfidenceUpdate:
    """Test ConfidenceUpdate model."""
    
    def test_confidence_update_creation(self):
        """Test creating a confidence update."""
        update = ConfidenceUpdate(
            node_uuid="test-uuid",
            old_value=0.5,
            new_value=0.7,
            trigger=ConfidenceTrigger.USER_REAFFIRMATION,
            reason="User reaffirmed",
            metadata={"context": "test"}
        )
        
        assert update.node_uuid == "test-uuid"
        assert update.old_value == 0.5
        assert update.new_value == 0.7
        assert update.trigger == ConfidenceTrigger.USER_REAFFIRMATION
        assert update.reason == "User reaffirmed"
        assert update.metadata == {"context": "test"}
        assert isinstance(update.timestamp, datetime)
    
        def test_confidence_update_default_timestamp(self):
        """Test that timestamp is automatically set."""
        from graphiti_core.utils.datetime_utils import utc_now
        
        before = utc_now()
        update = ConfidenceUpdate(
            node_uuid="test-uuid",
            old_value=0.5,
            new_value=0.7,
            trigger=ConfidenceTrigger.USER_REAFFIRMATION,
            reason="Test"
        )
        after = utc_now()

        assert isinstance(update.timestamp, datetime)
        # Should be between before and after (within reasonable bounds)
        assert before <= update.timestamp <= after


class TestConfidenceConfig:
    """Test ConfidenceConfig model."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ConfidenceConfig()
        
        # Initial confidence values
        assert config.initial_user_given == 0.8
        assert config.initial_inferred == 0.5
        assert config.initial_system_suggested == 0.4
        assert config.initial_duplicate_found == 0.1
        
        # Confidence increase values
        assert config.user_reaffirmation_boost == 0.1
        assert config.user_reference_boost == 0.05
        assert config.user_reasoning_boost == 0.03
        assert config.network_support_boost == 0.1
        assert config.reasoning_usage_boost == 0.05
        assert config.structural_support_boost == 0.05
        assert config.indirect_support_boost == 0.03
        assert config.consistency_boost == 0.02
        assert config.external_corroboration_boost == 0.01
        
        # Confidence decrease values
        assert config.contradiction_penalty == 0.3
        assert config.repeated_contradiction_penalty == 0.15
        assert config.user_correction_penalty == 0.1
        assert config.user_uncertainty_penalty == 0.1
        assert config.soft_contradiction_penalty == 0.05
        assert config.dormancy_decay_penalty == 0.05
        assert config.extended_dormancy_penalty == 0.1
        assert config.orphaned_entity_penalty == 0.15
        
        # Thresholds
        assert config.network_support_threshold == 0.75
        assert config.structural_support_threshold == 0.7
        assert config.structural_support_min_connections == 3
        assert config.dormancy_threshold_days == 30
        assert config.extended_dormancy_threshold_days == 90
        assert config.unstable_confidence_threshold == 0.4
        assert config.deletion_consideration_threshold == 0.2
        
        # Network propagation
        assert config.direct_connection_boost_factor == 0.1
        assert config.indirect_connection_boost_factor == 0.05
        assert config.propagation_threshold == 0.7
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = ConfidenceConfig(
            initial_user_given=0.9,
            contradiction_penalty=0.5,
            dormancy_threshold_days=60
        )
        
        assert config.initial_user_given == 0.9
        assert config.contradiction_penalty == 0.5
        assert config.dormancy_threshold_days == 60
        
        # Other values should remain default
        assert config.initial_inferred == 0.5
        assert config.network_support_threshold == 0.75 