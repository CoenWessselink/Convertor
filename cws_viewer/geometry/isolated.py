"""Crash-isolated native IFC tessellation worker.

OpenCascade boolean operations can terminate the native process for malformed
or numerically hostile source geometry.  The viewer must survive that: a
separate worker owns the native IFC/OCP session, and the coordinator can fall
back to an explicit proxy when the worker dies.
"""
from __future__ import annotations
import multiprocessing as mp
import os,time,traceback
from multiprocessing.connection import Connection
from typing import Any
from cws_viewer.contracts.geometry import CancelCheck,GeometryRequest,MeshData,TessellationSettings

PROVIDER_VERSION='cws-ifc-isolated-v1'
class NativeGeometryWorkerError(RuntimeError):pass

def _worker_main(connection:Connection)->None:
    # Import inside the child so no OCP state is inherited from the GUI process.
    from cws_viewer.geometry.ifc_provider import IfcMeshProvider
    provider=IfcMeshProvider()
    while True:
        try:message=connection.recv()
        except EOFError:return
        if message is None or message.get('command')=='shutdown':return
        try:
            request=message['request'];settings=message['settings'];mesh=provider.load(request,settings)
            connection.send({'ok':True,'mesh':mesh})
        except BaseException as exc:
            connection.send({'ok':False,'error':f'{type(exc).__name__}: {exc}','traceback':traceback.format_exc(limit=20)})

class IsolatedIfcMeshProvider:
    def __init__(self,*,timeout_seconds:float=120.0,start_method:str='spawn')->None:
        self.timeout_seconds=max(1.0,float(timeout_seconds));self._context=mp.get_context(start_method);self._process=None;self._connection=None;self._generation=0
    @property
    def provider_version(self):return PROVIDER_VERSION
    def supports(self,request:GeometryRequest)->bool:return request.source_format.upper()=='IFC'
    def _stop(self)->None:
        connection=self._connection;process=self._process;self._connection=None;self._process=None
        if connection is not None:
            try:connection.send({'command':'shutdown'})
            except Exception:pass
            try:connection.close()
            except Exception:pass
        if process is not None:
            process.join(timeout=1.0)
            if process.is_alive():process.terminate();process.join(timeout=2.0)
            try:process.close()
            except Exception:pass
    def _start(self)->None:
        self._stop();parent,child=self._context.Pipe(duplex=True);process=self._context.Process(target=_worker_main,args=(child,),name='CWS-IFC-Geometry-Worker',daemon=True);process.start();child.close();self._connection=parent;self._process=process;self._generation+=1
    def _ensure(self)->None:
        if self._process is None or self._connection is None or not self._process.is_alive():self._start()
    def load(self,request:GeometryRequest,settings:TessellationSettings,*,cancel_check:CancelCheck|None=None)->MeshData:
        self._ensure();assert self._connection is not None and self._process is not None
        try:self._connection.send({'command':'load','request':request,'settings':settings})
        except Exception as exc:
            code=self._process.exitcode;self._stop();raise NativeGeometryWorkerError(f'IFC-worker kon opdracht niet ontvangen (exitcode={code}): {exc}') from exc
        deadline=time.monotonic()+self.timeout_seconds
        while time.monotonic()<deadline:
            if cancel_check:
                try:cancel_check()
                except BaseException:self._stop();raise
            if self._connection.poll(0.05):
                try:reply=self._connection.recv()
                except EOFError as exc:
                    code=self._process.exitcode;self._stop();raise NativeGeometryWorkerError(f'IFC-worker stopte native tijdens tessellatie (exitcode={code})') from exc
                if reply.get('ok'):return reply['mesh']
                raise NativeGeometryWorkerError(str(reply.get('error') or 'Onbekende IFC-workerfout'))
            if not self._process.is_alive():
                code=self._process.exitcode;self._stop();raise NativeGeometryWorkerError(f'IFC-worker crashte tijdens tessellatie (exitcode={code})')
        self._stop();raise NativeGeometryWorkerError(f'IFC-worker timeout na {self.timeout_seconds:.1f} s')
    def close(self)->None:self._stop()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
    def __del__(self):
        try:self._stop()
        except Exception:pass

__all__=['IsolatedIfcMeshProvider','NativeGeometryWorkerError','PROVIDER_VERSION']
