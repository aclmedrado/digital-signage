"""Uso: python -m app.scripts.bootstrap_admin (sem argumentos)."""
import getpass
import sys
import warnings

from sqlalchemy.exc import SQLAlchemyError

from app.config import get_auth_settings
from app.database import Base, engine
from app.services.auth import BootstrapError, bootstrap_admin


def main():
    if len(sys.argv) != 1:
        print("Use python -m app.scripts.bootstrap_admin sem argumentos. Senhas não são aceitas na linha de comando.", file=sys.stderr)
        return 1
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        print("Bootstrap exige terminal interativo com entrada de senha oculta.", file=sys.stderr)
        return 1
    try:
        get_auth_settings()
        username = input("Usuário do primeiro administrador: ")
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            password = getpass.getpass("Senha (16–128 caracteres): ")
            confirmation = getpass.getpass("Confirme a senha: ")
        if password != confirmation:
            print("Confirmação diferente. Nenhuma conta criada.", file=sys.stderr)
            return 1
        Base.metadata.create_all(engine)
        bootstrap_admin(engine, username, password)
    except (BootstrapError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt, getpass.GetPassWarning):
        print("Bootstrap cancelado ou entrada oculta indisponível. Nenhuma conta criada.", file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print("Banco indisponível. Confira configuração e permissões; nenhum segredo foi registrado.", file=sys.stderr)
        return 1
    print("Primeiro administrador criado. Use somente HTTPS válido ou teste local isolado com túnel SSH.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
