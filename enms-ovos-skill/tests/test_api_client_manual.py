"""
Test script for EnMS API client
Validates connection and core endpoints
"""
import asyncio
import sys
from datetime import datetime, timedelta
sys.path.insert(0, '/home/ubuntu/ovos/enms-ovos-skill')

from lib.api_client import ENMSClient


async def test_api_client():
    """Test EnMS API client functionality"""
    
    # Initialize client
    client = ENMSClient(base_url="http://10.33.10.109:8001/api/v1")
    
    try:
        print("=" * 60)
        print("EnMS API Client Test Suite")
        print("=" * 60)
        
        # Test 1: Health Check
        print("\n[1] Testing health check...")
        health = await client.health_check()
        print(f"✅ Status: {health.get('status')}")
        print(f"   Service: {health.get('service')}")
        print(f"   Active machines: {health.get('active_machines')}")
        
        # Test 2: System Stats
        print("\n[2] Testing system stats...")
        stats = await client.system_stats()
        print(f"✅ Total energy: {stats.get('total_energy')} kWh")
        print(f"   Active machines today: {stats.get('active_machines_today')}")
        print(f"   Total anomalies: {stats.get('total_anomalies')}")
        
        # Test 3: List Machines
        print("\n[3] Testing list machines...")
        machines = await client.list_machines()
        print(f"✅ Found {len(machines)} machines:")
        for m in machines[:3]:
            print(f"   - {m['name']} ({m['type']}, {m['rated_power_kw']} kW)")
        
        # Test 4: Search Machines
        print("\n[4] Testing machine search...")
        compressors = await client.list_machines(search="compressor")
        print(f"✅ Found {len(compressors)} compressor(s):")
        for m in compressors:
            print(f"   - {m['name']} (ID: {m['id'][:8]}...)")
        
        # Test 5: Machine Status by Name
        if compressors:
            machine_name = compressors[0]['name']
            print(f"\n[5] Testing machine status for {machine_name}...")
            status = await client.get_machine_status(machine_name)
            print(f"✅ Status: {status['current_status']['status']}")
            print(f"   Power: {status['current_status']['power_kw']} kW")
            print(f"   Today energy: {status['today_stats']['energy_kwh']} kWh")
            print(f"   Cost: ${status['today_stats']['cost_usd']}")
        
        # Test 6: Factory Summary
        print("\n[6] Testing factory summary...")
        summary = await client.get_factory_summary()
        print(f"✅ Total consumption: {summary.get('total_consumption_kwh', 'N/A')} kWh")
        print(f"   Active machines: {summary.get('active_machines', 'N/A')}")
        
        # Test 7: Top Consumers
        print("\n[7] Testing top consumers...")
        top = await client.get_top_consumers(limit=3)
        print(f"✅ Top 3 energy consumers:")
        if 'machines' in top:
            for i, m in enumerate(top['machines'][:3], 1):
                print(f"   {i}. {m.get('machine_name')}: {m.get('total_energy_kwh')} kWh")
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await client.close()
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_api_client())
    sys.exit(0 if success else 1)
