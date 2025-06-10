"""
Service WebSockets pour RobianAPI
Communication temps réel avec les clients
"""

import json
import asyncio
import logging
from typing import Dict, List, Set, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import weakref

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types de messages WebSocket"""
    # Client vers serveur
    CONNECT = "connect"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"
    
    # Serveur vers client
    CONNECTED = "connected"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBED = "unsubscribed"
    PONG = "pong"
    ERROR = "error"
    
    # Notifications
    DEBATE_STARTED = "debate_started"
    DEBATE_ENDED = "debate_ended"
    EXTRACTION_STARTED = "extraction_started"
    EXTRACTION_COMPLETED = "extraction_completed"
    EXTRACTION_FAILED = "extraction_failed"
    SYSTEM_STATUS = "system_status"


class ChannelType(str, Enum):
    """Types de canaux de diffusion"""
    DEBATES = "debates"
    EXTRACTIONS = "extractions"
    SYSTEM = "system"
    USER_SPECIFIC = "user"


@dataclass
class WebSocketMessage:
    """Structure d'un message WebSocket"""
    type: MessageType
    channel: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    message_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire pour sérialisation"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result
    
    def to_json(self) -> str:
        """Conversion en JSON"""
        return json.dumps(self.to_dict())


class WebSocketConnection:
    """Représente une connexion WebSocket client"""
    
    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.subscriptions: Set[str] = set()
        self.connected_at = datetime.now()
        self.last_ping = datetime.now()
        self.user_id: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
    
    async def send_message(self, message: WebSocketMessage):
        """Envoyer un message au client"""
        try:
            await self.websocket.send_text(message.to_json())
            logger.debug(f"📤 Message envoyé à {self.client_id}: {message.type}")
        except Exception as e:
            logger.error(f"❌ Erreur envoi message à {self.client_id}: {e}")
            raise
    
    async def ping(self):
        """Envoyer un ping au client"""
        ping_message = WebSocketMessage(type=MessageType.PING)
        await self.send_message(ping_message)
        self.last_ping = datetime.now()
    
    def is_subscribed_to(self, channel: str) -> bool:
        """Vérifier si le client est abonné à un canal"""
        return channel in self.subscriptions
    
    def subscribe(self, channel: str):
        """S'abonner à un canal"""
        self.subscriptions.add(channel)
        logger.debug(f"🔔 Client {self.client_id} abonné à {channel}")
    
    def unsubscribe(self, channel: str):
        """Se désabonner d'un canal"""
        self.subscriptions.discard(channel)
        logger.debug(f"🔕 Client {self.client_id} désabonné de {channel}")


class WebSocketManager:
    """Gestionnaire des connexions WebSocket"""
    
    def __init__(self):
        # Utilisation de WeakSet pour éviter les fuites mémoire
        self.connections: Dict[str, WebSocketConnection] = {}
        self.channels: Dict[str, Set[str]] = {}  # channel -> set of client_ids
        self.message_history: Dict[str, List[WebSocketMessage]] = {}
        self.max_history_per_channel = 100
        
        # Task de nettoyage des connexions inactives
        self.cleanup_task: Optional[asyncio.Task] = None
        self.cleanup_interval = 60  # secondes
    
    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None) -> str:
        """Accepter une nouvelle connexion WebSocket"""
        await websocket.accept()
        
        if client_id is None:
            client_id = str(uuid.uuid4())
        
        connection = WebSocketConnection(websocket, client_id)
        self.connections[client_id] = connection
        
        # Message de bienvenue
        welcome_message = WebSocketMessage(
            type=MessageType.CONNECTED,
            data={
                "client_id": client_id,
                "server_time": datetime.now().isoformat(),
                "available_channels": list(ChannelType)
            }
        )
        await connection.send_message(welcome_message)
        
        logger.info(f"🔌 Nouvelle connexion WebSocket: {client_id}")
        
        # Démarrer le nettoyage si c'est la première connexion
        if len(self.connections) == 1 and self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._cleanup_inactive_connections())
        
        return client_id
    
    async def disconnect(self, client_id: str):
        """Fermer une connexion WebSocket"""
        if client_id in self.connections:
            connection = self.connections[client_id]
            
            # Désabonner de tous les canaux
            for channel in list(connection.subscriptions):
                await self._unsubscribe_from_channel(client_id, channel)
            
            # Supprimer la connexion
            del self.connections[client_id]
            
            logger.info(f"🔌 Connexion fermée: {client_id}")
            
            # Arrêter le nettoyage si plus de connexions
            if len(self.connections) == 0 and self.cleanup_task:
                self.cleanup_task.cancel()
                self.cleanup_task = None
    
    async def handle_message(self, client_id: str, message_data: str):
        """Traiter un message reçu d'un client"""
        try:
            message_dict = json.loads(message_data)
            message_type = MessageType(message_dict.get("type"))
            
            connection = self.connections.get(client_id)
            if not connection:
                logger.warning(f"⚠️ Message de client déconnecté: {client_id}")
                return
            
            if message_type == MessageType.PING:
                await self._handle_ping(connection)
            elif message_type == MessageType.SUBSCRIBE:
                await self._handle_subscribe(connection, message_dict)
            elif message_type == MessageType.UNSUBSCRIBE:
                await self._handle_unsubscribe(connection, message_dict)
            else:
                logger.warning(f"⚠️ Type de message non géré: {message_type}")
        
        except json.JSONDecodeError:
            logger.error(f"❌ Message JSON invalide de {client_id}: {message_data}")
            await self._send_error(client_id, "Invalid JSON format")
        except ValueError as e:
            logger.error(f"❌ Type de message invalide de {client_id}: {e}")
            await self._send_error(client_id, f"Invalid message type: {e}")
        except Exception as e:
            logger.error(f"❌ Erreur traitement message de {client_id}: {e}")
            await self._send_error(client_id, "Internal server error")
    
    async def _handle_ping(self, connection: WebSocketConnection):
        """Traiter un ping du client"""
        connection.last_ping = datetime.now()
        pong_message = WebSocketMessage(type=MessageType.PONG)
        await connection.send_message(pong_message)
    
    async def _handle_subscribe(self, connection: WebSocketConnection, message_dict: Dict):
        """Traiter une demande d'abonnement"""
        channel = message_dict.get("channel")
        if not channel:
            await self._send_error(connection.client_id, "Channel name required for subscription")
            return
        
        # Validation du canal
        valid_channels = [c.value for c in ChannelType] + [f"user:{connection.user_id}"]
        if channel not in valid_channels and not channel.startswith("debate:"):
            await self._send_error(connection.client_id, f"Invalid channel: {channel}")
            return
        
        await self._subscribe_to_channel(connection.client_id, channel)
        
        # Envoyer confirmation
        response = WebSocketMessage(
            type=MessageType.SUBSCRIBED,
            channel=channel,
            data={"subscribed_to": channel}
        )
        await connection.send_message(response)
        
        # Envoyer l'historique récent du canal si disponible
        await self._send_channel_history(connection, channel)
    
    async def _handle_unsubscribe(self, connection: WebSocketConnection, message_dict: Dict):
        """Traiter une demande de désabonnement"""
        channel = message_dict.get("channel")
        if not channel:
            await self._send_error(connection.client_id, "Channel name required for unsubscription")
            return
        
        await self._unsubscribe_from_channel(connection.client_id, channel)
        
        # Envoyer confirmation
        response = WebSocketMessage(
            type=MessageType.UNSUBSCRIBED,
            channel=channel,
            data={"unsubscribed_from": channel}
        )
        await connection.send_message(response)
    
    async def _subscribe_to_channel(self, client_id: str, channel: str):
        """Abonner un client à un canal"""
        connection = self.connections.get(client_id)
        if not connection:
            return
        
        connection.subscribe(channel)
        
        # Ajouter au canal global
        if channel not in self.channels:
            self.channels[channel] = set()
        self.channels[channel].add(client_id)
    
    async def _unsubscribe_from_channel(self, client_id: str, channel: str):
        """Désabonner un client d'un canal"""
        connection = self.connections.get(client_id)
        if connection:
            connection.unsubscribe(channel)
        
        # Retirer du canal global
        if channel in self.channels:
            self.channels[channel].discard(client_id)
            if not self.channels[channel]:
                del self.channels[channel]
    
    async def _send_channel_history(self, connection: WebSocketConnection, channel: str):
        """Envoyer l'historique récent d'un canal"""
        if channel in self.message_history:
            history = self.message_history[channel][-10:]  # 10 derniers messages
            for message in history:
                try:
                    await connection.send_message(message)
                except Exception:
                    # Ignorer les erreurs d'envoi d'historique
                    pass
    
    async def _send_error(self, client_id: str, error_message: str):
        """Envoyer un message d'erreur à un client"""
        connection = self.connections.get(client_id)
        if connection:
            error_msg = WebSocketMessage(
                type=MessageType.ERROR,
                data={"error": error_message}
            )
            try:
                await connection.send_message(error_msg)
            except Exception:
                # Si on ne peut pas envoyer l'erreur, déconnecter
                await self.disconnect(client_id)
    
    async def broadcast_to_channel(self, channel: str, message: WebSocketMessage):
        """Diffuser un message à tous les clients d'un canal"""
        if channel not in self.channels:
            logger.debug(f"📢 Canal {channel} n'a aucun abonné")
            return
        
        # Sauvegarder dans l'historique
        self._save_to_history(channel, message)
        
        # Envoyer à tous les clients du canal
        client_ids = list(self.channels[channel])  # Copie pour éviter modification pendant itération
        disconnected_clients = []
        
        for client_id in client_ids:
            connection = self.connections.get(client_id)
            if connection and connection.is_subscribed_to(channel):
                try:
                    await connection.send_message(message)
                except Exception as e:
                    logger.error(f"❌ Erreur envoi à {client_id}: {e}")
                    disconnected_clients.append(client_id)
        
        # Nettoyer les connexions fermées
        for client_id in disconnected_clients:
            await self.disconnect(client_id)
        
        logger.debug(f"📢 Message diffusé sur {channel} à {len(client_ids)} clients")
    
    async def send_to_user(self, user_id: str, message: WebSocketMessage):
        """Envoyer un message à un utilisateur spécifique"""
        user_channel = f"user:{user_id}"
        await self.broadcast_to_channel(user_channel, message)
    
    def _save_to_history(self, channel: str, message: WebSocketMessage):
        """Sauvegarder un message dans l'historique du canal"""
        if channel not in self.message_history:
            self.message_history[channel] = []
        
        self.message_history[channel].append(message)
        
        # Limiter la taille de l'historique
        if len(self.message_history[channel]) > self.max_history_per_channel:
            self.message_history[channel] = self.message_history[channel][-self.max_history_per_channel:]
    
    async def _cleanup_inactive_connections(self):
        """Task de nettoyage des connexions inactives"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                now = datetime.now()
                inactive_threshold = timedelta(minutes=5)  # 5 minutes sans ping
                
                inactive_clients = []
                for client_id, connection in self.connections.items():
                    if now - connection.last_ping > inactive_threshold:
                        inactive_clients.append(client_id)
                
                # Déconnecter les clients inactifs
                for client_id in inactive_clients:
                    logger.info(f"🧹 Déconnexion client inactif: {client_id}")
                    await self.disconnect(client_id)
                
                if inactive_clients:
                    logger.info(f"🧹 Nettoyé {len(inactive_clients)} connexions inactives")
                
            except asyncio.CancelledError:
                logger.info("🛑 Task de nettoyage WebSocket arrêtée")
                break
            except Exception as e:
                logger.error(f"❌ Erreur nettoyage WebSocket: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Statistiques des connexions WebSocket"""
        return {
            "total_connections": len(self.connections),
            "total_channels": len(self.channels),
            "channels_info": {
                channel: len(clients) 
                for channel, clients in self.channels.items()
            },
            "connections_by_age": {
                "under_1min": sum(1 for c in self.connections.values() 
                                if datetime.now() - c.connected_at < timedelta(minutes=1)),
                "under_5min": sum(1 for c in self.connections.values() 
                                if datetime.now() - c.connected_at < timedelta(minutes=5)),
                "over_5min": sum(1 for c in self.connections.values() 
                               if datetime.now() - c.connected_at >= timedelta(minutes=5)),
            },
            "message_history_size": sum(len(msgs) for msgs in self.message_history.values())
        }


# Instance globale du gestionnaire WebSocket
websocket_manager = WebSocketManager()


# Fonctions de notification prêtes à l'emploi
async def notify_debate_started(debate_id: str, debate_data: Dict[str, Any]):
    """Notifier le début d'un débat"""
    message = WebSocketMessage(
        type=MessageType.DEBATE_STARTED,
        channel=ChannelType.DEBATES,
        data={
            "debate_id": debate_id,
            "debate": debate_data,
            "action": "started"
        }
    )
    await websocket_manager.broadcast_to_channel(ChannelType.DEBATES, message)
    await websocket_manager.broadcast_to_channel(f"debate:{debate_id}", message)


async def notify_debate_ended(debate_id: str, debate_data: Dict[str, Any]):
    """Notifier la fin d'un débat"""
    message = WebSocketMessage(
        type=MessageType.DEBATE_ENDED,
        channel=ChannelType.DEBATES,
        data={
            "debate_id": debate_id,
            "debate": debate_data,
            "action": "ended"
        }
    )
    await websocket_manager.broadcast_to_channel(ChannelType.DEBATES, message)
    await websocket_manager.broadcast_to_channel(f"debate:{debate_id}", message)


async def notify_extraction_started(debate_id: str, extraction_id: str):
    """Notifier le début d'une extraction audio"""
    message = WebSocketMessage(
        type=MessageType.EXTRACTION_STARTED,
        channel=ChannelType.EXTRACTIONS,
        data={
            "debate_id": debate_id,
            "extraction_id": extraction_id,
            "status": "started",
            "estimated_duration": "5-10 minutes"
        }
    )
    await websocket_manager.broadcast_to_channel(ChannelType.EXTRACTIONS, message)
    await websocket_manager.broadcast_to_channel(f"debate:{debate_id}", message)


async def notify_extraction_completed(debate_id: str, extraction_id: str, audio_url: str, file_size: int):
    """Notifier la fin d'une extraction audio"""
    message = WebSocketMessage(
        type=MessageType.EXTRACTION_COMPLETED,
        channel=ChannelType.EXTRACTIONS,
        data={
            "debate_id": debate_id,
            "extraction_id": extraction_id,
            "status": "completed",
            "audio_url": audio_url,
            "file_size": file_size,
            "format": "mp3"
        }
    )
    await websocket_manager.broadcast_to_channel(ChannelType.EXTRACTIONS, message)
    await websocket_manager.broadcast_to_channel(f"debate:{debate_id}", message)


async def notify_extraction_failed(debate_id: str, extraction_id: str, error: str):
    """Notifier l'échec d'une extraction audio"""
    message = WebSocketMessage(
        type=MessageType.EXTRACTION_FAILED,
        channel=ChannelType.EXTRACTIONS,
        data={
            "debate_id": debate_id,
            "extraction_id": extraction_id,
            "status": "failed",
            "error": error
        }
    )
    await websocket_manager.broadcast_to_channel(ChannelType.EXTRACTIONS, message)
    await websocket_manager.broadcast_to_channel(f"debate:{debate_id}", message)


async def notify_system_status(status: str, details: Dict[str, Any]):
    """Notifier le statut du système"""
    message = WebSocketMessage(
        type=MessageType.SYSTEM_STATUS,
        channel=ChannelType.SYSTEM,
        data={
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
    )
    await websocket_manager.broadcast_to_channel(ChannelType.SYSTEM, message)


# Middleware d'intégration pour FastAPI
class WebSocketMiddleware:
    """Middleware pour intégrer les WebSockets dans l'application"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        # Ajouter le gestionnaire WebSocket au scope pour l'utiliser dans les routes
        scope["websocket_manager"] = websocket_manager
        await self.app(scope, receive, send)
