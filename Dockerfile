FROM python:3.10.2 as base

FROM base AS python-deps

RUN pip install pipenv
RUN apt-get update && apt-get install -y --no-install-recommends gcc

COPY Pipfile .
COPY Pipfile.lock .
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy

FROM base AS runtime

COPY --from=python-deps /.venv /.venv

ENV PATH="/.venv/bin:$PATH"

COPY . .

ENV PYTHONPATH "./"
ENV MONGO_DETAILS=mongodb+srv://dev:W6gt602lJXdM0erf@cluster0.5aw7x.mongodb.net/?retryWrites=true&w=majority
ENV ENV=prod

CMD ["python","-u","main.py"]