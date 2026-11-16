from ephemeris.services.kernels import kernel_signature


def test_kernel_signature_uses_contents_and_remains_independent_of_directory(tmp_path, monkeypatch):
	first_directory = tmp_path / 'first'
	second_directory = tmp_path / 'second'
	first_directory.mkdir()
	second_directory.mkdir()
	first_path = first_directory / 'kernel.bsp'
	second_path = second_directory / 'kernel.bsp'
	first_path.write_bytes(b'first')
	second_path.write_bytes(b'first')
	monkeypatch.setattr('ephemeris.services.kernels.kernel_paths', lambda: [first_path])
	first_signature = kernel_signature()
	monkeypatch.setattr('ephemeris.services.kernels.kernel_paths', lambda: [second_path])

	assert kernel_signature() == first_signature
	second_path.write_bytes(b'other')
	assert kernel_signature() != first_signature
