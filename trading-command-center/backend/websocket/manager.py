"""
WebSocket Connection Manager untuk Trading Command Center
Mengelola WebSocket connections dan real-time data broadcasting
"""

import asyncio
import json
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
from collections import defaultdict
from utils.logger import setup_logging

logger = setup_logging()


class ConnectionManager:
    """Manager untuk WebSocket connections dan real-time data"""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = defaultdict(list)
        self.subscriptions: Dict[WebSocket, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))
        self.connection_metadata: Dict[WebSocket, Dict] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        # Start background tasks
        asyncio.create_task(self._message_processor())
        asyncio.create_task(self._connection_monitor())
        
    async def connect(self, websocket: WebSocket):
        """Handle new WebSocket connection"""
        try:
            await websocket.accept()
            connection_id = f"conn_{datetime.now().timestamp()}"
            
            # Store connection metadata
            self.connection_metadata[websocket] = {
                'id': connection_id,
                'connected_at': datetime.now(),
                'last_heartbeat': datetime.now(),
                'message_count': 0
            }
            
            logger.info(f"✅ WebSocket connected: {connection_id}")
            
        except Exception as e:
            logger.error(f"❌ Error accepting WebSocket connection: {e}")
            
    def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection"""
        try:
            # Remove dari semua subscriptions
            if websocket in self.subscriptions:
                del self.subscriptions[websocket]
                
            # Remove dari active connections
            for channel, connections in self.active_connections.items():
                if websocket in connections:
                    connections.remove(websocket)
                    
            # Remove metadata
            if websocket in self.connection_metadata:
                connection_id = self.connection_metadata[websocket]['id']
                del self.connection_metadata[websocket]
                logger.info(f"🔌 WebSocket disconnected: {connection_id}")
                
        except Exception as e:
            logger.error(f"❌ Error disconnecting WebSocket: {e}")
            
    async def subscribe(self, websocket: WebSocket, channel: str, symbol: Optional[str] = None):
        """Subscribe WebSocket ke channel"""
        try:
            if symbol:
                self.subscriptions[websocket][channel].add(symbol)
                logger.info(f"📡 WebSocket subscribed to {channel}:{symbol}")
            else:
                self.subscriptions[websocket][channel].add('*')  # All symbols
                logger.info(f"📡 WebSocket subscribed to {channel}:*")
                
            # Add ke active connections untuk channel
            if websocket not in self.active_connections[channel]:
                self.active_connections[channel].append(websocket)
                
            # Send confirmation
            await self.send_personal_message(websocket, {
                'type': 'subscribed',
                'channel': channel,
                'symbol': symbol,
                'status': 'success'
            })
            
        except Exception as e:
            logger.error(f"❌ Error subscribing WebSocket: {e}")
            
    async def unsubscribe(self, websocket: WebSocket, channel: str, symbol: Optional[str] = None):
        """Unsubscribe WebSocket dari channel"""
        try:
            if symbol and symbol in self.subscriptions[websocket][channel]:
                self.subscriptions[websocket][channel].remove(symbol)
                logger.info(f"📡 WebSocket unsubscribed from {channel}:{symbol}")
            elif symbol is None:
                self.subscriptions[websocket][channel].clear()
                self.subscriptions[websocket][channel].add('*')
                logger.info(f"📡 WebSocket unsubscribed from {channel}:*")
                
            # Remove dari active connections jika tidak ada subscription lain
            has_other_subs = any(
                subs for ch, subs in self.subscriptions[websocket].items() 
                if ch != channel and subs
            )
            
            if not has_other_subs and websocket in self.active_connections[channel]:
                self.active_connections[channel].remove(websocket)
                
            # Send confirmation
            await self.send_personal_message(websocket, {
                'type': 'unsubscribed',
                'channel': channel,
                'symbol': symbol,
                'status': 'success'
            })
            
        except Exception as e:
            logger.error(f"❌ Error unsubscribing WebSocket: {e}")
            
    async def broadcast(self, message: Dict[str, Any], channel: str, symbol: Optional[str] = None):
        """Broadcast message ke semua subscribers di channel"""
        try:
            # Queue message untuk processing
            await self.message_queue.put({
                'message': message,
                'channel': channel,
                'symbol': symbol,
                'timestamp': datetime.now()
            })
            
        except Exception as e:
            logger.error(f"❌ Error queuing broadcast message: {e}")
            
    async def send_personal_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send personal message ke specific WebSocket"""
        try:
            # default=str: payload berisi datetime; send_json akan gagal dan memutus klien
            await websocket.send_text(json.dumps(message, default=str))
            
            # Update message count
            if websocket in self.connection_metadata:
                self.connection_metadata[websocket]['message_count'] += 1
                
        except (WebSocketDisconnect, RuntimeError) as e:
            # klien menutup tab/koneksi saat broadcast: kejadian normal, bukan error
            logger.info(f"🔌 Klien terputus saat kirim pesan ({type(e).__name__})")
            self.disconnect(websocket)
        except Exception as e:
            logger.error(f"❌ Error sending personal message: {type(e).__name__}: {e}")
            self.disconnect(websocket)
            
    async def _message_processor(self):
        """Background task untuk process broadcast messages"""
        while True:
            try:
                # Get message dari queue
                message_data = await self.message_queue.get()
                message = message_data['message']
                channel = message_data['channel']
                symbol = message_data.get('symbol')
                
                # Get connections untuk channel
                connections = self.active_connections.get(channel, [])
                
                # Send ke setiap connection yang sesuai
                send_tasks = []
                for connection in connections[:]:
                    if self._should_send_to_connection(connection, channel, symbol):
                        send_tasks.append(self.send_personal_message(connection, message))
                        
                # Execute sends concurrently
                if send_tasks:
                    await asyncio.gather(*send_tasks, return_exceptions=True)
                    
                # Mark task as done
                self.message_queue.task_done()
                
            except Exception as e:
                logger.error(f"❌ Error processing broadcast message: {e}")
                
    def _should_send_to_connection(self, websocket: WebSocket, channel: str, symbol: Optional[str]) -> bool:
        """Check apakah message harus dikirim ke connection"""
        try:
            if websocket not in self.subscriptions:
                return False
                
            channel_subs = self.subscriptions[websocket].get(channel, set())
            
            # Check if symbol specific atau all symbols
            if symbol:
                return symbol in channel_subs or '*' in channel_subs
            else:
                return '*' in channel_subs or len(channel_subs) > 0
                
        except Exception as e:
            logger.error(f"❌ Error checking subscription: {e}")
            return False
            
    async def _connection_monitor(self):
        """Monitor WebSocket connections dan cleanup"""
        while True:
            try:
                current_time = datetime.now()
                connections_to_remove = []
                
                # Check setiap connection
                for websocket, metadata in self.connection_metadata.items():
                    last_heartbeat = metadata['last_heartbeat']
                    
                    # Remove jika tidak aktif lebih dari 5 menit
                    if (current_time - last_heartbeat).total_seconds() > 300:
                        connections_to_remove.append(websocket)
                        
                # Remove inactive connections
                for websocket in connections_to_remove:
                    logger.info(f"🧹 Removing inactive connection: {self.connection_metadata.get(websocket, {}).get('id', 'unknown')}")
                    self.disconnect(websocket)
                    
                # Wait sebelum next check
                await asyncio.sleep(60)  # Check setiap menit
                
            except Exception as e:
                logger.error(f"❌ Error in connection monitor: {e}")
                
    async def heartbeat(self, websocket: WebSocket):
        """Update heartbeat untuk connection"""
        try:
            if websocket in self.connection_metadata:
                self.connection_metadata[websocket]['last_heartbeat'] = datetime.now()
                
        except Exception as e:
            logger.error(f"❌ Error updating heartbeat: {e}")
            
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""
        try:
            stats = {
                'total_connections': len(self.connection_metadata),
                'channels': {},
                'connection_details': []
            }
            
            # Channel statistics
            for channel, connections in self.active_connections.items():
                stats['channels'][channel] = len(connections)
                
            # Connection details
            for websocket, metadata in self.connection_metadata.items():
                stats['connection_details'].append({
                    'id': metadata['id'],
                    'connected_at': metadata['connected_at'].isoformat(),
                    'message_count': metadata['message_count'],
                    'subscriptions': list(self.subscriptions.get(websocket, {}).keys())
                })
                
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting connection stats: {e}")
            return {}
            
    async def broadcast_system_status(self, status: str, message: str):
        """Broadcast system status ke semua connections"""
        try:
            system_message = {
                'type': 'system_status',
                'status': status,
                'message': message,
                'timestamp': datetime.now().isoformat()
            }
            
            # Send ke semua active connections
            for channel in self.active_connections.keys():
                await self.broadcast(system_message, channel)
                
        except Exception as e:
            logger.error(f"❌ Error broadcasting system status: {e}")
            
    async def cleanup(self):
        """Cleanup semua connections"""
        try:
            logger.info("🧹 Cleaning up WebSocket connections...")
            
            # Close semua connections
            for connections in self.active_connections.values():
                for websocket in connections[:]:
                    try:
                        await websocket.close()
                    except:
                        pass
                        
            # Clear semua data structures
            self.active_connections.clear()
            self.subscriptions.clear()
            self.connection_metadata.clear()
            
            logger.info("✅ WebSocket cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Error during WebSocket cleanup: {e}")