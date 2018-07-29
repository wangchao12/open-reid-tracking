from __future__ import print_function, absolute_import
import os.path as osp

from ..utils.data import Dataset
from ..utils.osutils import mkdir_if_missing
from ..utils.serialization import write_json


class DukeTo1501(Dataset):

    def __init__(self, root, split_id=0, num_val=10, download=True):
        super(DukeTo1501, self).__init__(root, split_id=split_id)

        if download:
            self.download()

        # if not self._check_integrity():
        #     raise RuntimeError("Dataset not found or corrupted. " +
        #                        "You can use download=True to download it.")

        self.load(num_val)

    def download(self):
        # if self._check_integrity():
        #     print("Files already downloaded and verified")
        #     return

        import re
        import hashlib
        import shutil
        from glob import glob
        from zipfile import ZipFile

        market_raw_dir = osp.join(self.root, 'market_raw')
        mkdir_if_missing(market_raw_dir)
        # Download the raw zip file
        fpath = osp.join(market_raw_dir, 'Market-1501-v15.09.15.zip')
        # if osp.isfile(fpath) and \
        #   hashlib.md5(open(fpath, 'rb').read()).hexdigest() == self.md5:
        #     print("Using downloaded file: " + fpath)
        # else:
        #     raise RuntimeError("Please download the dataset manually from {} "
        #                        "to {}".format(self.url, fpath))

        # Extract the file
        exdir = osp.join(market_raw_dir, 'Market-1501-v15.09.15')
        if not osp.isdir(exdir):
            print("Extracting zip file")
            with ZipFile(fpath) as z:
                z.extractall(path=market_raw_dir)

        # Format
        images_dir = osp.join(self.root, 'images')
        mkdir_if_missing(images_dir)
        duke_raw_dir = osp.join(self.root, 'duke_raw')

        # 1501 identities (+1 for background) with 6 camera views each
        # and more than 7000 ids from dukemtmc
        identities = [[[] for _ in range(8)] for _ in range(20000)]

        def market_register(subdir, pattern=re.compile(r'([-\d]+)_c(\d)')):
            fpaths = sorted(glob(osp.join(exdir, subdir, '*.jpg')))
            pids = set()
            for fpath in fpaths:
                fname = osp.basename(fpath)
                pid, cam = map(int, pattern.search(fname).groups())
                if pid == -1: continue  # junk images are just ignored
                assert 0 <= pid <= 1501  # pid == 0 means background
                assert 1 <= cam <= 6
                cam -= 1
                pid += 10000  # NOW, pid == 10000 means background
                pids.add(pid)
                fname = ('{:08d}_{:02d}_{:04d}.jpg'
                         .format(pid, cam, len(identities[pid][cam])))
                identities[pid][cam].append(fname)
                shutil.copy(fpath, osp.join(images_dir, fname))
            return pids

        def duke_register(pattern=re.compile(r'([-\d]+)_c(\d)')):
            fpaths = sorted(glob(osp.join(duke_raw_dir, '*.jpg')))
            pids = set()
            for fpath in fpaths:
                fname = osp.basename(fpath)
                pid, cam = map(int, pattern.search(fname).groups())
                if pid == -1: continue  # junk images are just ignored
                assert 0 <= pid <= 8000  # pid == 0 means background
                assert 1 <= cam <= 8
                cam -= 1
                pids.add(pid)
                # fname = ('{:08d}_{:02d}_{:04d}.jpg'.format(pid, cam, len(identities[pid][cam])))
                identities[pid][cam].append(fname)
                # shutil.copy(fpath, osp.join(images_dir, fname))
            return pids

        trainval_pids = duke_register()
        gallery_pids = market_register('bounding_box_test')
        query_pids = market_register('query')
        assert query_pids <= gallery_pids
        assert trainval_pids.isdisjoint(gallery_pids)

        # Save meta information into a json file
        meta = {'name': 'DukeTo1501', 'shot': 'multiple', 'num_cameras': 8,
                'identities': identities}
        write_json(meta, osp.join(self.root, 'meta.json'))

        # Save the only training / test split
        splits = [{
            'trainval': sorted(list(trainval_pids)),
            'query': sorted(list(query_pids)),
            'gallery': sorted(list(gallery_pids))}]
        write_json(splits, osp.join(self.root, 'splits.json'))
