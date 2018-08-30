FROM fermipy/fermipy:latest
MAINTAINER Stephan Zimmer <zimmer@slac.stanford.edu>
RUN conda install -c cython numpy astropy click regions
RUN python -m pip install --user git+https://github.com/gammapy/gammapy.git
CMD ["usleep 10 && /opt/conda/bin/jupyter notebook --notebook-dir=/workdir --ip='*' --port=8888 --no-browser --allow-root"]
ENTRYPOINT ["/bin/bash","--login","-c"]
