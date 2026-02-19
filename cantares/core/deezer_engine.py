"""
Motor de descarga FLAC desde Deezer para Cantares.
Implementa el protocolo de descarga/descifrado directamente,
sin depender del CLI de deemix.

Flujo: Login ARL -> Search/Get Track -> Generate URL -> Download Stream -> Blowfish Decrypt -> Tag FLAC/MP3
"""

import os
import re
import sys
import time
import logging
import requests
from pathlib import Path
from hashlib import md5 as hashlib_md5
from binascii import a2b_hex, b2a_hex
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, List

from Crypto.Cipher import Blowfish, AES
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger('cantares.deezer')


# ============================================================
#  Constantes y Configuracion
# ============================================================

class Quality(Enum):
    FLAC = "FLAC"
    MP3_320 = "MP3_320"
    MP3_128 = "MP3_128"


QUALITY_MAP = {
    Quality.FLAC:    {"format_n": 9,  "format_name": "FLAC",    "ext": ".flac"},
    Quality.MP3_320: {"format_n": 3,  "format_name": "MP3_320", "ext": ".mp3"},
    Quality.MP3_128: {"format_n": 1,  "format_name": "MP3_128", "ext": ".mp3"},
}

# Deezer crypto keys (del protocolo publico deemix/deezloader)
_SECRET = "g4el58wc0zvf9na1"
_AES_KEY = b"jo6aey6haid2Teih"
_BF_IV = a2b_hex("0001020304050607")

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
)
_GW_URL = "https://www.deezer.com/ajax/gw-light.php"


# ============================================================
#  Crypto (27 lineas - todo lo necesario)
# ============================================================

def _md5hex(data) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib_md5(data).hexdigest()


def _gen_bf_key(track_id: str) -> bytes:
    h = _md5hex(track_id)
    return bytes(
        ord(h[i]) ^ ord(h[i + 16]) ^ ord(_SECRET[i])
        for i in range(16)
    )


def _decrypt_chunk(key: bytes, data: bytes) -> bytes:
    return Blowfish.new(key, Blowfish.MODE_CBC, _BF_IV).decrypt(data)


def _gen_stream_path(sng_id, md5_origin, media_version, format_n) -> str:
    url_part = b"\xa4".join([
        md5_origin.encode(),
        str(format_n).encode(),
        str(sng_id).encode(),
        str(media_version).encode()
    ])
    md5val = _md5hex(url_part).encode()
    step2 = md5val + b"\xa4" + url_part + b"\xa4"
    step2 += b"." * (16 - (len(step2) % 16))
    encrypted = AES.new(_AES_KEY, AES.MODE_ECB).encrypt(step2)
    return b2a_hex(encrypted).decode("utf-8")


def _gen_stream_url(sng_id, md5_origin, media_version, format_n) -> str:
    path = _gen_stream_path(sng_id, md5_origin, media_version, format_n)
    return f"https://cdns-proxy-{md5_origin[0]}.dzcdn.net/mobile/1/{path}"


# ============================================================
#  Resultado de descarga
# ============================================================

@dataclass
class DeezerResult:
    success: bool
    title: str = ""
    artist: str = ""
    filepath: str = ""
    quality: str = ""
    size_bytes: int = 0
    error: str = ""
    source: str = "deezer"


@dataclass 
class DeezerBatchResult:
    total: int = 0
    ok: int = 0
    failed: int = 0
    skipped: int = 0
    results: List[DeezerResult] = field(default_factory=list)
    elapsed: float = 0.0


# ============================================================
#  Motor Principal
# ============================================================

class DeezerEngine:
    """Motor de descarga FLAC/MP3 desde Deezer."""

    def __init__(self, output_dir: str = "Downloads", 
                 quality: Quality = Quality.FLAC,
                 arl: str = None,
                 progress_callback: Callable = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.quality = quality
        self.arl = arl or os.getenv("DEEZER_ARL", "")
        self.progress_callback = progress_callback
        self._cancelled = False
        
        # Session HTTP
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": _USER_AGENT})
        
        # State
        self.token = None
        self.license_token = None
        self.user_name = ""
        self.can_lossless = False
        self.can_hq = False
        self.logged_in = False

    # ----------------------------------------------------------
    #  Login
    # ----------------------------------------------------------
    
    def login(self) -> bool:
        """Login con ARL cookie."""
        if not self.arl:
            logger.error("No ARL token provided")
            return False
        
        self.session.cookies.set("arl", self.arl, domain=".deezer.com")
        
        try:
            data = self._gw("deezer.getUserData")
            if not data:
                return False
            
            user = data.get("USER", {})
            if user.get("USER_ID", 0) == 0:
                logger.error("ARL invalido o expirado")
                return False
            
            self.token = data.get("checkForm")
            opts = user.get("OPTIONS", {})
            self.license_token = opts.get("license_token")
            self.can_lossless = opts.get("web_lossless", False) or opts.get("mobile_lossless", False)
            self.can_hq = opts.get("web_hq", False) or opts.get("mobile_hq", False)
            self.user_name = user.get("BLOG_NAME", "Unknown")
            self.logged_in = True
            
            logger.info("Logged in as: %s (FLAC=%s, HQ=%s)", 
                        self.user_name, self.can_lossless, self.can_hq)
            return True
            
        except Exception as e:
            logger.error("Login failed: %s", e)
            return False

    # ----------------------------------------------------------
    #  Busqueda
    # ----------------------------------------------------------
    
    def search(self, query: str, limit: int = 5) -> list:
        """Buscar tracks en Deezer."""
        body = {
            "query": query,
            "filter": "ALL",
            "output": "TRACK",
            "start": 0,
            "nb": limit
        }
        result = self._gw("search.music", body)
        if not result or "data" not in result:
            return []
        return result["data"]

    def search_best_match(self, artist: str, title: str) -> Optional[dict]:
        """Buscar el mejor match para artista + titulo."""
        query = f"{artist} {title}"
        results = self.search(query, limit=5)
        if not results:
            return None
        
        # Intentar match exacto primero
        artist_lower = artist.lower()
        title_lower = title.lower()
        for track in results:
            t_artist = track.get("ART_NAME", "").lower()
            t_title = track.get("SNG_TITLE", "").lower()
            if artist_lower in t_artist and title_lower in t_title:
                return track
        
        # Si no, devolver el primer resultado
        return results[0]

    # ----------------------------------------------------------
    #  Descarga Individual
    # ----------------------------------------------------------
    
    def download_track(self, artist: str, title: str, 
                       album: str = "", track_num: int = 0) -> DeezerResult:
        """Descargar un track por artista + titulo."""
        if self._cancelled:
            return DeezerResult(success=False, error="Cancelado")
        
        if not self.logged_in:
            if not self.login():
                return DeezerResult(
                    success=False, title=title, artist=artist,
                    error="No se pudo autenticar con Deezer (ARL invalido?)"
                )
        
        # 1) Buscar track
        track_data = self.search_best_match(artist, title)
        if not track_data:
            return DeezerResult(
                success=False, title=title, artist=artist,
                error=f"Track no encontrado en Deezer: {artist} - {title}"
            )
        
        sng_id = str(track_data.get("SNG_ID", ""))
        return self.download_by_id(sng_id, artist_hint=artist, title_hint=title)

    def download_by_id(self, sng_id: str, 
                       artist_hint: str = "", title_hint: str = "") -> DeezerResult:
        """Descargar un track por su ID de Deezer."""
        try:
            # 1) Obtener metadata completa del track
            track_info = self._gw("song.getData", {"SNG_ID": sng_id})
            if not track_info:
                return DeezerResult(
                    success=False, title=title_hint, artist=artist_hint,
                    error=f"No se pudo obtener datos del track {sng_id}"
                )
            
            artist = track_info.get("ART_NAME", artist_hint)
            title = track_info.get("SNG_TITLE", title_hint)
            album = track_info.get("ALB_TITLE", "")
            md5_origin = track_info.get("MD5_ORIGIN", "")
            media_version = track_info.get("MEDIA_VERSION", "")
            track_token = track_info.get("TRACK_TOKEN", "")
            
            if not md5_origin:
                return DeezerResult(
                    success=False, title=title, artist=artist,
                    error="Track sin MD5 (no codificado todavia)"
                )
            
            # 2) Resolver calidad y obtener URL
            quality, url = self._resolve_url(
                sng_id, md5_origin, media_version, track_token
            )
            if not url:
                return DeezerResult(
                    success=False, title=title, artist=artist,
                    error=f"No se pudo obtener URL de descarga (calidad {self.quality.value})"
                )
            
            # 3) Generar filepath
            q_info = QUALITY_MAP[quality]
            safe_name = self._sanitize_filename(f"{artist} - {title}")
            filepath = self.output_dir / f"{safe_name}{q_info['ext']}"
            
            # Skip si existe
            if filepath.exists():
                size = filepath.stat().st_size
                return DeezerResult(
                    success=True, title=title, artist=artist,
                    filepath=str(filepath), quality=quality.value,
                    size_bytes=size
                )
            
            # 4) Descargar y descifrar
            bf_key = _gen_bf_key(sng_id)
            self._download_and_decrypt(url, filepath, bf_key)
            
            if not filepath.exists():
                return DeezerResult(
                    success=False, title=title, artist=artist,
                    error="Archivo no creado despues de descarga"
                )
            
            # 5) Tag metadata
            cover_url = self._get_cover_url(track_info)
            self._tag_file(filepath, track_info, cover_url)
            
            size = filepath.stat().st_size
            return DeezerResult(
                success=True, title=title, artist=artist,
                filepath=str(filepath), quality=quality.value,
                size_bytes=size
            )
            
        except Exception as e:
            logger.exception("Error descargando track %s", sng_id)
            return DeezerResult(
                success=False, title=title_hint, artist=artist_hint,
                error=str(e)
            )

    # ----------------------------------------------------------
    #  Descarga Batch
    # ----------------------------------------------------------
    
    def download_batch(self, tracks: list, 
                       progress_cb: Callable = None) -> DeezerBatchResult:
        """
        Descargar multiples tracks.
        tracks: lista de dicts con 'artist' y 'title' (y opcionalmente 'album').
        """
        start_time = time.time()
        result = DeezerBatchResult(total=len(tracks))
        
        for i, track in enumerate(tracks):
            if self._cancelled:
                break
            
            artist = track.get("artist", "")
            title = track.get("title", "")
            
            if progress_cb:
                progress_cb(i, len(tracks), f"[{i+1}/{len(tracks)}] {artist} - {title}")
            
            dl_result = self.download_track(artist, title)
            result.results.append(dl_result)
            
            if dl_result.success:
                if dl_result.size_bytes > 0 and dl_result.filepath:
                    result.ok += 1
                else:
                    result.skipped += 1
            else:
                result.failed += 1
        
        result.elapsed = time.time() - start_time
        return result

    def cancel(self):
        self._cancelled = True

    # ----------------------------------------------------------
    #  Internos: GW API
    # ----------------------------------------------------------
    
    def _gw(self, method: str, body: dict = None) -> Optional[dict]:
        """Llamada a la GW API de Deezer."""
        if body is None:
            body = {}
        
        params = {
            "api_version": "1.0",
            "api_token": self.token if self.token else "null",
            "input": "3",
            "method": method
        }
        
        try:
            resp = self.session.post(_GW_URL, params=params, json=body, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("error"):
                err = data["error"]
                # Token expirado -> refrescar
                if err in [
                    {"GATEWAY_ERROR": "invalid api token"},
                    {"VALID_TOKEN_REQUIRED": "Invalid CSRF token"}
                ]:
                    self._refresh_token()
                    params["api_token"] = self.token
                    resp = self.session.post(_GW_URL, params=params, json=body, timeout=30)
                    data = resp.json()
                else:
                    logger.warning("GW API error (%s): %s", method, err)
                    return None
            
            # Extraer token si es getUserData
            if method == "deezer.getUserData" and not self.token:
                self.token = data.get("results", {}).get("checkForm")
            
            return data.get("results")
            
        except Exception as e:
            logger.error("GW API request failed (%s): %s", method, e)
            return None

    def _refresh_token(self):
        """Refrescar el token CSRF."""
        try:
            old_token = self.token
            self.token = "null"
            data = self._gw("deezer.getUserData")
            if data:
                self.token = data.get("checkForm", old_token)
        except Exception:
            pass

    # ----------------------------------------------------------
    #  Internos: Resolucion de URL
    # ----------------------------------------------------------
    
    def _resolve_url(self, sng_id, md5_origin, media_version, track_token) -> tuple:
        """
        Intenta obtener URL de descarga, con fallback de calidad.
        Retorna (Quality, url) o (None, None).
        """
        # Orden de calidades a intentar
        fallback_chain = {
            Quality.FLAC: [Quality.FLAC, Quality.MP3_320, Quality.MP3_128],
            Quality.MP3_320: [Quality.MP3_320, Quality.MP3_128],
            Quality.MP3_128: [Quality.MP3_128],
        }
        
        for q in fallback_chain.get(self.quality, [Quality.MP3_128]):
            q_info = QUALITY_MAP[q]
            
            # Metodo 1: API moderna (media.deezer.com) — necesita license_token
            if track_token and self.license_token:
                url = self._get_url_via_api(track_token, q_info["format_name"])
                if url and self._test_url(url):
                    return (q, url)
            
            # Metodo 2: URL legacy (generada con crypto)
            url = _gen_stream_url(sng_id, md5_origin, media_version, q_info["format_n"])
            if self._test_url(url):
                return (q, url)
        
        return (None, None)

    def _get_url_via_api(self, track_token: str, format_name: str) -> Optional[str]:
        """Obtener URL via media API (metodo moderno)."""
        try:
            resp = self.session.post(
                "https://media.deezer.com/v1/get_url",
                json={
                    "license_token": self.license_token,
                    "media": [{
                        "type": "FULL",
                        "formats": [
                            {"cipher": "BF_CBC_STRIPE", "format": format_name}
                        ]
                    }],
                    "track_tokens": [track_token]
                },
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            
            if data.get("data"):
                for item in data["data"]:
                    if "media" in item and item["media"]:
                        sources = item["media"][0].get("sources", [])
                        if sources:
                            url = sources[0]["url"]
                            # Force standard CDN if mobile proxy is returned
                            if "e-cdns-proxy" in url:
                                url = url.replace("e-cdns-proxy", "cdns-proxy")
                            return url
        except Exception as e:
            logger.debug("Media API fallback: %s", e)
        
        return None

    def _test_url(self, url: str) -> bool:
        """Verificar que la URL es accesible."""
        try:
            resp = requests.head(url, headers={"User-Agent": _USER_AGENT}, timeout=10)
            return resp.status_code == 200 and int(resp.headers.get("Content-Length", 0)) > 0
        except Exception:
            return False

    # ----------------------------------------------------------
    #  Internos: Download + Decrypt
    # ----------------------------------------------------------
    
    def _download_and_decrypt(self, url: str, filepath: Path, bf_key: bytes):
        """Descargar stream cifrado y descifrar chunk por chunk."""
        try:
            resp = self.session.get(url, stream=True, timeout=30)
            resp.raise_for_status()
            
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            is_crypted = "/mobile/" in url or "/media/" in url
            
            with open(filepath, 'wb') as f:
                is_start = True
                for chunk in resp.iter_content(2048 * 3):  # 6144 bytes
                    if self._cancelled:
                        break
                    
                    if is_crypted and len(chunk) >= 2048:
                        # Descifrar primeros 2048 bytes de cada chunk
                        chunk = _decrypt_chunk(bf_key, chunk[:2048]) + chunk[2048:]
                    
                    # Limpiar bytes nulos al inicio
                    if is_start and chunk[0] == 0:
                        try:
                            if chunk[4:8].decode('utf-8') != "ftyp":
                                for i, byte in enumerate(chunk):
                                    if byte != 0:
                                        break
                                chunk = chunk[i:]
                        except (UnicodeDecodeError, IndexError):
                            pass
                    is_start = False
                    
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if self.progress_callback and total > 0:
                        pct = (downloaded / total) * 100
                        self.progress_callback(pct)
                        
        except Exception as e:
            # Limpiar archivo parcial
            if filepath.exists():
                filepath.unlink()
            raise e

    # ----------------------------------------------------------
    #  Internos: Tagging
    # ----------------------------------------------------------
    
    def _tag_file(self, filepath: Path, track_info: dict, cover_url: str = None):
        """Agregar metadata al archivo descargado."""
        ext = filepath.suffix.lower()
        
        try:
            if ext == ".flac":
                self._tag_flac(filepath, track_info, cover_url)
            elif ext == ".mp3":
                self._tag_mp3(filepath, track_info, cover_url)
        except Exception as e:
            logger.warning("Error tagging %s: %s", filepath.name, e)

    def _tag_flac(self, filepath: Path, info: dict, cover_url: str):
        """Tag archivo FLAC con mutagen."""
        try:
            from mutagen.flac import FLAC
            from mutagen.flac import Picture
            
            audio = FLAC(str(filepath))
            audio["title"] = info.get("SNG_TITLE", "")
            audio["artist"] = info.get("ART_NAME", "")
            audio["album"] = info.get("ALB_TITLE", "")  
            audio["tracknumber"] = str(info.get("TRACK_NUMBER", ""))
            audio["date"] = info.get("PHYSICAL_RELEASE_DATE", "")[:4] if info.get("PHYSICAL_RELEASE_DATE") else ""
            
            if info.get("ISRC"):
                audio["isrc"] = info["ISRC"]
            
            # Cover art
            if cover_url:
                try:
                    img_data = requests.get(cover_url, timeout=10).content
                    pic = Picture()
                    pic.type = 3  # Front cover
                    pic.mime = "image/jpeg"
                    pic.data = img_data
                    audio.add_picture(pic)
                except Exception:
                    pass
            
            audio.save()
        except ImportError:
            logger.warning("mutagen no disponible para tagging FLAC")
        except Exception as e:
            logger.warning("FLAC tag error: %s", e)

    def _tag_mp3(self, filepath: Path, info: dict, cover_url: str):
        """Tag archivo MP3 con mutagen."""
        try:
            from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TDRC, APIC, TSRC
            from mutagen.id3 import ID3NoHeaderError
            
            try:
                tags = ID3(str(filepath))
            except ID3NoHeaderError:
                tags = ID3()
            
            tags.add(TIT2(encoding=3, text=[info.get("SNG_TITLE", "")]))
            tags.add(TPE1(encoding=3, text=[info.get("ART_NAME", "")]))
            tags.add(TALB(encoding=3, text=[info.get("ALB_TITLE", "")]))
            tags.add(TRCK(encoding=3, text=[str(info.get("TRACK_NUMBER", ""))]))
            
            date = info.get("PHYSICAL_RELEASE_DATE", "")[:4] if info.get("PHYSICAL_RELEASE_DATE") else ""
            if date:
                tags.add(TDRC(encoding=3, text=[date]))
            
            if info.get("ISRC"):
                tags.add(TSRC(encoding=3, text=[info["ISRC"]]))
            
            # Cover art
            if cover_url:
                try:
                    img_data = requests.get(cover_url, timeout=10).content
                    tags.add(APIC(
                        encoding=3, mime="image/jpeg",
                        type=3, desc="Cover", data=img_data
                    ))
                except Exception:
                    pass
            
            tags.save(str(filepath))
        except ImportError:
            logger.warning("mutagen no disponible para tagging MP3")
        except Exception as e:
            logger.warning("MP3 tag error: %s", e)

    # ----------------------------------------------------------
    #  Utilidades
    # ----------------------------------------------------------
    
    def _get_cover_url(self, track_info: dict, size: int = 1000) -> str:
        """Obtener URL de la portada del album."""
        alb_pic = track_info.get("ALB_PICTURE", "")
        if alb_pic:
            return f"https://cdns-images.dzcdn.net/images/cover/{alb_pic}/{size}x{size}-000000-80-0-0.jpg"
        return ""

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Limpiar nombre de archivo."""
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        name = name.strip('. ')
        return name[:200]  # Limitar longitud
