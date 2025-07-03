---
title: Custom Entity and Edge Types
subtitle: Enhancing Graphiti with Custom Ontologies
---

Graphiti allows you to define custom entity types and edge types to better represent your domain-specific knowledge. This enables more structured data extraction and richer semantic relationships in your knowledge graph.

## Defining Custom Entity and Edge Types

Custom entity types and edge types are defined using Pydantic models. Each model represents a specific type with custom attributes.

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# Custom Entity Types
class Person(BaseModel):
    """A person entity with biographical information."""
    age: Optional[int] = Field(None, description="Age of the person")
    occupation: Optional[str] = Field(None, description="Current occupation")
    location: Optional[str] = Field(None, description="Current location")
    birth_date: Optional[datetime] = Field(None, description="Date of birth")

class Company(BaseModel):
    """A business organization."""
    industry: Optional[str] = Field(None, description="Primary industry")
    founded_year: Optional[int] = Field(None, description="Year company was founded")
    headquarters: Optional[str] = Field(None, description="Location of headquarters")
    employee_count: Optional[int] = Field(None, description="Number of employees")

class Product(BaseModel):
    """A product or service."""
    category: Optional[str] = Field(None, description="Product category")
    price: Optional[float] = Field(None, description="Price in USD")
    release_date: Optional[datetime] = Field(None, description="Product release date")

# Custom Edge Types
class Employment(BaseModel):
    """Employment relationship between a person and company."""
    position: Optional[str] = Field(None, description="Job title or position")
    start_date: Optional[datetime] = Field(None, description="Employment start date")
    end_date: Optional[datetime] = Field(None, description="Employment end date")
    salary: Optional[float] = Field(None, description="Annual salary in USD")
    is_current: Optional[bool] = Field(None, description="Whether employment is current")

class Investment(BaseModel):
    """Investment relationship between entities."""
    amount: Optional[float] = Field(None, description="Investment amount in USD")
    investment_type: Optional[str] = Field(None, description="Type of investment (equity, debt, etc.)")
    stake_percentage: Optional[float] = Field(None, description="Percentage ownership")
    investment_date: Optional[datetime] = Field(None, description="Date of investment")

class Partnership(BaseModel):
    """Partnership relationship between companies."""
    partnership_type: Optional[str] = Field(None, description="Type of partnership")
    duration: Optional[str] = Field(None, description="Expected duration")
    deal_value: Optional[float] = Field(None, description="Financial value of partnership")
```

## Using Custom Entity and Edge Types

Pass your custom entity types and edge types to the add_episode method:

```python
entity_types = {
    "Person": Person,
    "Company": Company,
    "Product": Product
}

edge_types = {
    "Employment": Employment,
    "Investment": Investment,
    "Partnership": Partnership
}

edge_type_map = {
    ("Person", "Company"): ["Employment"],
    ("Company", "Company"): ["Partnership", "Investment"],
    ("Person", "Person"): ["Partnership"],
    ("Entity", "Entity"): ["Investment"],  # Apply to any entity type
}

await graphiti.add_episode(
    name="Business Update",
    episode_body="Sarah joined TechCorp as CTO in January 2023 with a $200K salary. TechCorp partnered with DataCorp in a $5M deal.",
    source_description="Business news",
    reference_time=datetime.now(),
    entity_types=entity_types,
    edge_types=edge_types,
    edge_type_map=edge_type_map
)
```

## Searching with Custom Types

You can filter search results to specific entity types or edge types using SearchFilters:

```python
from graphiti_core.search.search_filters import SearchFilters

# Search for only specific entity types
search_filter = SearchFilters(
    node_labels=["Person", "Company"]  # Only return Person and Company entities
)

results = await graphiti.search_(
    query="Who works at tech companies?",
    search_filter=search_filter
)

# Search for only specific edge types
search_filter = SearchFilters(
    edge_types=["Employment", "Partnership"]  # Only return Employment and Partnership edges
)

results = await graphiti.search_(
    query="Tell me about business relationships",
    search_filter=search_filter
)
```

## How Custom Types Work

### Entity Extraction Process

1. **Extraction**: Graphiti extracts entities from text and classifies them using your custom types
2. **Validation**: Each entity is validated against the appropriate Pydantic model
3. **Attribute Population**: Custom attributes are extracted from the text and populated
4. **Storage**: Entities are stored with their custom attributes

### Edge Extraction Process

1. **Relationship Detection**: Graphiti identifies relationships between extracted entities
2. **Type Classification**: Based on the entity types involved and your edge_type_map, relationships are classified
3. **Attribute Extraction**: For custom edge types, additional attributes are extracted from the context
4. **Validation**: Edge attributes are validated against the Pydantic model
5. **Storage**: Edges are stored with their custom attributes and relationship metadata

## Edge Type Mapping

The edge_type_map parameter defines which edge types can exist between specific entity type pairs:

```python
edge_type_map = {
    ("Person", "Company"): ["Employment"],
    ("Company", "Company"): ["Partnership", "Investment"],
    ("Person", "Person"): ["Partnership"],
    ("Entity", "Entity"): ["Investment"],  # Apply to any entity type
}
```

If an entity pair doesn't have a defined edge type mapping, Graphiti will use default relationship types and the relationship will still be captured with a generic RELATES_TO type.

## Schema Evolution

Your knowledge graph's schema can evolve over time as your needs change. You can update entity types by adding new attributes to existing types without breaking existing nodes. When you add new attributes, existing nodes will preserve their original attributes while supporting the new ones for future updates. This flexible approach allows your knowledge graph to grow and adapt while maintaining backward compatibility with historical data.

For example, if you initially defined a "Customer" type with basic attributes like name and email, you could later add attributes like "loyalty_tier" or "acquisition_channel" without needing to modify or migrate existing customer nodes in your graph.

## Best Practices

### Model Design

- **Clear Descriptions**: Always include detailed descriptions in docstrings and Field descriptions
- **Optional Fields**: Make custom attributes optional to handle cases where information isn't available
- **Appropriate Types**: Use specific types (datetime, int, float) rather than strings when possible
- **Validation**: Consider adding Pydantic validators for complex validation rules
- **Atomic Attributes**: Attributes should be broken down into their smallest meaningful units rather than storing compound information

```python
from pydantic import validator

class Person(BaseModel):
    """A person entity."""
    age: Optional[int] = Field(None, description="Age in years")
    
    @validator('age')
    def validate_age(cls, v):
        if v is not None and (v < 0 or v > 150):
            raise ValueError('Age must be between 0 and 150')
        return v
```

**Instead of compound information:**
```python
class Customer(BaseModel):
    contact_info: Optional[str] = Field(None, description="Name and email")  # Don't do this
```

**Use atomic attributes:**
```python
class Customer(BaseModel):
    name: Optional[str] = Field(None, description="Customer name")
    email: Optional[str] = Field(None, description="Customer email address")
```

### Naming Conventions

- **Entity Types**: Use PascalCase (e.g., Person, TechCompany)
- **Edge Types**: Use PascalCase for custom types (e.g., Employment, Partnership)
- **Attributes**: Use snake_case (e.g., start_date, employee_count)
- **Descriptions**: Be specific and actionable for the LLM
- **Consistency**: Maintain consistent naming conventions across related entity types

### Edge Type Mapping Strategy

- **Specific Mappings**: Define specific entity type pairs for targeted relationships
- **Fallback to Entity**: Use ("Entity", "Entity") as a fallback for general relationships
- **Balanced Scope**: Don't make edge types too specific or too general
- **Domain Coverage**: Ensure your edge types cover the main relationships in your domain

```python
# Good: Specific and meaningful
edge_type_map = {
    ("Person", "Company"): ["Employment", "Investment"],
    ("Company", "Company"): ["Partnership", "Acquisition"],
    ("Person", "Product"): ["Usage", "Review"],
    ("Entity", "Entity"): ["RELATES_TO"]  # Fallback for unexpected relationships
}

# Avoid: Too granular
edge_type_map = {
    ("CEO", "TechCompany"): ["CEOEmployment"],
    ("Engineer", "TechCompany"): ["EngineerEmployment"],
    # This creates too many specific types
}
```

## Entity Type Exclusion

You can exclude specific entity types from extraction using the excluded_entity_types parameter:

```python
await graphiti.add_episode(
    name="Business Update",
    episode_body="The meeting discussed various topics including weather and sports.",
    source_description="Meeting notes",
    reference_time=datetime.now(),
    entity_types=entity_types,
    excluded_entity_types=["Person"]  # Won't extract Person entities
)
```

## Migration Guide

If you're upgrading from a previous version of Graphiti:

- You can add entity types to new episodes, even if existing episodes in the graph did not have entity types. Existing nodes will continue to work without being classified.
- To add types to previously ingested data, you need to re-ingest it with entity types set into a new graph.

## Important Constraints

### Protected Attribute Names

Custom entity type attributes cannot use protected names that are already used by Graphiti's core EntityNode class:
- `uuid`, `name`, `group_id`, `labels`, `created_at`, `summary`, `attributes`, `name_embedding`

Custom entity types and edge types provide powerful ways to structure your knowledge graph according to your domain needs. They enable more precise extraction, better organization, and richer semantic relationships in your data.






"""
Copyright 2024, Zep Software, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import asyncio
import logging
import os
import sys
from uuid import uuid4

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from transcript_parser import parse_podcast_messages

from graphiti_core import Graphiti
from graphiti_core.utils.maintenance.graph_data_operations import clear_data


from graphiti_extend import ExtendedGraphiti

load_dotenv()

neo4j_uri = os.environ.get('NEO4J_URI') or 'bolt://localhost:7687'
neo4j_user = os.environ.get('NEO4J_USER') or 'neo4j'
neo4j_password = os.environ.get('NEO4J_PASSWORD') or 'password'


def setup_logging():
    # Create a logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # Set the logging level to INFO

    # Create console handler and set level to INFO
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Add formatter to console handler
    console_handler.setFormatter(formatter)

    # Add console handler to logger
    logger.addHandler(console_handler)

    return logger


class Person(BaseModel):
    """A human person, fictional or nonfictional."""

    first_name: str | None = Field(..., description='First name')
    last_name: str | None = Field(..., description='Last name')
    occupation: str | None = Field(..., description="The person's work occupation")


class IsPresidentOf(BaseModel):
    """Relationship between a person and the entity they are a president of"""


async def main():
    setup_logging()

    client = ExtendedGraphiti(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USERNAME,
            password=settings.NEO4J_PASSWORD,
            enable_contradiction_detection=enable_contradiction_detection,
            contradiction_threshold=contradiction_threshold
        )
    await clear_data(client.driver)
    await client.build_indices_and_constraints()
    messages = parse_podcast_messages()
    group_id = str(uuid4())

    for i, message in enumerate(messages[3:14]):
        episodes = await client.retrieve_episodes(message.actual_timestamp, 3, group_ids=[group_id])
        episode_uuids = [episode.uuid for episode in episodes]

        await client.add_episode_with_contradictions(
            name=f'Message {i}',
            episode_body=f'{message.speaker_name} ({message.role}): {message.content}',
            reference_time=message.actual_timestamp,
            source_description='Podcast Transcript',
            group_id=group_id,
            entity_types={'Person': Person},
            edge_types={'IS_PRESIDENT_OF': IsPresidentOf},
            edge_type_map={('Person', 'Entity'): ['PRESIDENT_OF']},
            previous_episode_uuids=episode_uuids,
        )


asyncio.run(main())
