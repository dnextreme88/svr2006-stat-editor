"""Yuke's PAC archive reader / rebuilder.  Python 3 port."""
import os

from control import pac_file
from str_op import string_get_file_extension
import apppaths


def log_int(n, base=10):
    if n == 0:
        raise ArithmeticError
    res = 0
    while n != 0:
        n //= base
        res += 1
    return res - 1


class PAC(object):

    def __init__(self, filename, name_id=0):
        self.file = pac_file(filename)
        self.filename = filename
        self.type = self.file.read_string(4)
        if self.type == b"PAC ":
            self.name_size = 2
            self.offset_size = 3
            self.size_size = 3
        elif self.type == b"PACH":
            self.name_size = 4
            self.offset_size = 4
            self.size_size = 4
        else:
            raise IOError("%r is not a PAC/PACH archive (magic %r)"
                          % (filename, self.type))
        self.file.seek(4)
        self.entry = self.file.read_int(4)
        self.the_toc = []
        for _ in range(self.entry):
            _fileno = self.file.read_int(self.name_size)
            _address = self.file.read_int(self.offset_size)
            _size = self.file.read_int(self.size_size)
            self.the_toc.append((_fileno, _address, _size))
        self.file_address = self.file.tell()
        self.name_id = name_id

        self.duplicated_dict = {}
        file_no_list = [toc[0] for toc in self.the_toc]
        for _fileno in file_no_list:
            if _fileno in self.duplicated_dict:
                continue
            if file_no_list.count(_fileno) > 1:
                self.duplicated_dict[_fileno] = [
                    i for i, n in enumerate(file_no_list) if n == _fileno]

    def close(self):
        self.file.close()

    def is_dir(self, index):
        return False

    def get_file_extension(self, index):
        _fileno, _address, _size = self.the_toc[index]
        self.file.seek(_address + self.file_address)
        return string_get_file_extension(self.file.read_string(4))

    def get_useless_data(self, index):
        """The alignment padding that follows entry `index`."""
        _fileno, _address, _size = self.the_toc[index]
        if index < len(self.the_toc) - 1:
            _address2 = self.the_toc[index + 1][1]
        else:
            _address2 = os.path.getsize(self.filename)
        _useless_address = self.file_address + _address + _size
        if index < len(self.the_toc) - 1:
            _useless_size = self.file_address + _address2 - _useless_address
        else:
            _useless_size = _address2 - _useless_address
        self.file.seek(_useless_address)
        return self.file.read_string(_useless_size)

    def get_file_name(self, index):
        if self.name_id == 0:
            return "file%.6d" % index
        fileno = self.the_toc[index][0]
        digits = 1 if fileno == 0 else log_int(fileno, 16) + 1
        if digits % 2 == 1:
            digits += 1
        if self.name_id == 2 and digits < 4:
            digits = 4
        name = "%.*X" % (digits, fileno)
        if fileno in self.duplicated_dict:
            name = "%s[%d]" % (name, self.duplicated_dict[fileno].index(index))
        return name

    def get_file_address(self, index):
        return self.the_toc[index][1] + self.file_address

    def get_file_size(self, index):
        return self.the_toc[index][2]

    def filename_to_index(self, filename):
        filename = filename.lower()
        for x in range(self.entry):
            file = self.get_file_name(x)
            x_filename = ("%s%s" % (file, self.get_file_extension(x))).lower()
            if filename == x_filename or filename == ("%s.dat" % file).lower():
                return x
        return -1

    def read(self, filename):
        index = self.filename_to_index(filename)
        if index == -1:
            raise IOError("no entry named %r in %r" % (filename, self.filename))
        _fileno, _address, _size = self.the_toc[index]
        self.file.seek(_address + self.file_address)
        return self.file.read_string(_size)

    def namelist(self):
        return ["%s%s" % (self.get_file_name(x), self.get_file_extension(x))
                for x in range(self.entry)]

    def extract_info(self, _filename=None):
        if _filename is None:
            _filename = "%s_info.txt" % self.filename
        with open(_filename, "w") as output:
            for x in range(self.entry):
                file_no = self.the_toc[x][0]
                fmt = "ID: %.4X, %s%s\n" if self.type == b"PAC " else "ID: %.8X, %s%s\n"
                output.write(fmt % (file_no, self.get_file_name(x),
                                    self.get_file_extension(x)))

    def extract_file(self, index, _filename=None, is_gui=False):
        if _filename is None:
            _dirname = "@%s" % self.filename
            if not os.path.exists(_dirname):
                os.makedirs(_dirname)
            _filename = os.path.join(
                _dirname, self.get_file_name(index) + self.get_file_extension(index))
        _fileno, _address, _size = self.the_toc[index]
        self.file.seek(_address + self.file_address)
        with open(_filename, "wb+") as output:
            output.write(self.file.read_string(_size))
        if not is_gui:
            print("File extracted: %r" % _filename)

    def extract_all(self, is_gui=False, _dirname=None):
        if _dirname is None:
            _dirname = "@%s" % self.filename
        if not os.path.exists(_dirname):
            os.makedirs(_dirname)
        for x in range(self.entry):
            _filename = os.path.join(
                _dirname, self.get_file_name(x) + self.get_file_extension(x))
            self.extract_file(x, _filename, is_gui)

    def rebuild(self, _get_useless_data=True, is_gui=False, dirname=None):
        """Reassemble the archive from `dirname`, writing <filename>-NEW."""
        if dirname is None:
            dirname = "@%s" % self.filename
        tmp = apppaths.tmp_dir()
        toc_path = os.path.join(tmp, "temp1")
        body_path = os.path.join(tmp, "temp2")

        with open(toc_path, "wb") as _temp1, open(body_path, "wb") as _temp2:
            _temp1.write(self.type)
            _temp1.write(int(self.entry).to_bytes(4, "little"))
            _addr = 0
            for x in range(self.entry):
                _filename = self.get_file_name(x)
                _extension = self.get_file_extension(x)
                _path = os.path.join(dirname, _filename + _extension)
                if not os.path.exists(_path):
                    _path = os.path.join(dirname, _filename + ".dat")
                _size = os.path.getsize(_path)
                with open(_path, "rb") as fh:
                    _data = fh.read()

                if not is_gui:
                    print("Step %d: Processing file %s%s" % (x, _filename, _extension))

                if _get_useless_data:
                    _useless_data = self.get_useless_data(x)
                else:
                    _useless_data = b"\x00" * ((4 - _size % 4) if _size % 4 else 0)

                _temp2.write(_data)
                _temp2.write(_useless_data)

                _fileno = self.the_toc[x][0]
                if not is_gui:
                    print("- Data starts at 0x%.6X" % _addr)
                    print("- Size 0x%.4X bytes" % _size)
                _temp1.write(int(_fileno).to_bytes(self.name_size, "little"))
                _temp1.write(int(_addr).to_bytes(self.offset_size, "little"))
                _temp1.write(int(_size).to_bytes(self.size_size, "little"))
                _addr += _size + len(_useless_data)

        with open("%s-NEW" % self.filename, "wb") as output:
            with open(toc_path, "rb") as fh:
                output.write(fh.read())
            with open(body_path, "rb") as fh:
                output.write(fh.read())
            _total_size = output.tell()
            if _total_size % 2048:
                output.write(b"\x00" * (2048 - _total_size % 2048))

        os.remove(toc_path)
        os.remove(body_path)
