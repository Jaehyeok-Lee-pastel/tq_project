import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("app")


class UserFacingPermissionError(PermissionError):
    """Permission errors whose message is safe to show to the client.

    Plain PermissionError (e.g. OS file permissions) must NOT be mapped to a
    client response, so handlers match this subclass only.
    """


def register_exception_handlers(app: FastAPI) -> None:
    """Separate user-facing errors from internal ones.

    HTTPExceptions already return a clean {"detail": ...} body. This adds a
    catch-all so unexpected exceptions are logged server-side but never leak
    internals to the client (returns a generic 500).
    """

    @app.exception_handler(UserFacingPermissionError)
    async def permission_error(request: Request, exc: UserFacingPermissionError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
