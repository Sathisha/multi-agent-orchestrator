import asyncio
import json
import os
import sys
from uuid import uuid4
from sqlalchemy import select

# Add parent directory to sys.path to find shared module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.database.connection import get_async_db_context
from shared.models.chain import Chain, ChainNode, ChainEdge, ChainStatus

async def seed_samples():
    print("Seed script started...")
    
    # Path inside container
    samples_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shared', 'data', 'sample_chains.json')
    if not os.path.exists(samples_path):
        print(f"Error: Samples file not found at {samples_path}")
        return

    with open(samples_path, 'r') as f:
        samples = json.load(f)

    async with get_async_db_context() as session:
        for sample in samples:
            # Check if chain already exists
            print(f"Checking for existing chain: {sample['name']}")
            result = await session.execute(
                select(Chain).where(Chain.name == sample['name'])
            )
            if result.scalar_one_or_none():
                print(f"Skipping: Chain '{sample['name']}' already exists.")
                continue

            print(f"Creating chain: {sample['name']}")
            chain = Chain(
                name=sample['name'],
                description=sample.get('description', ''),
                category=sample.get('category', 'General'),
                status=sample.get('status', ChainStatus.DRAFT),
                tags=sample.get('tags', [])
            )
            session.add(chain)
            await session.flush()

            # Create Nodes
            for node_data in sample['nodes']:
                node = ChainNode(
                    chain_id=chain.id,
                    node_id=node_data['node_id'],
                    node_type=node_data['node_type'],
                    label=node_data['label'],
                    position_x=node_data['position_x'],
                    position_y=node_data['position_y'],
                    config=node_data.get('config', {}),
                    order_index=node_data.get('order_index', 0)
                )
                session.add(node)

            # Create Edges
            for edge_data in sample['edges']:
                edge = ChainEdge(
                    chain_id=chain.id,
                    edge_id=edge_data['edge_id'],
                    source_node_id=edge_data['source_node_id'],
                    target_node_id=edge_data['target_node_id'],
                    condition=edge_data.get('condition'),
                    label=edge_data.get('label')
                )
                session.add(edge)

        await session.commit()
        print("Seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_samples())
