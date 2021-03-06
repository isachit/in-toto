"""
<Program Name>
  common.py

<Author>
  Lukas Puehringer <lukas.puehringer@nyu.edu>
  Santiago Torres <santiago@nyu.edu>

<Started>
  Sep 23, 2016

<Copyright>
  See LICENSE for licensing information.

<Purpose>
  Provides base classes for various classes in the model.

<Classes>
  Metablock:
      pretty printed canonical JSON representation and dump

  Signable:
      sign self, store signature to self and verify signatures

"""

import attr
import canonicaljson
import inspect

import securesystemslib.keys
import securesystemslib.formats
from in_toto.exceptions import SignatureVerificationError

@attr.s(repr=False)
class Metablock(object):
  """Objects with base class Metablock have a __repr__ method
  that returns a canonical pretty printed JSON string and can be dumped to a
  file """
  def __repr__(self):
    return canonicaljson.encode_pretty_printed_json(attr.asdict(self))

  def dump(self, filename):
    with open(filename, 'wt') as fp:
      fp.write("{}".format(self))

  def validate(self):
    """
      <Purpose>
        Inspects the class (or subclass) for validate methods to ensure the
        all its members are properly formed. This method can be used to ensure
        the metadata contained in this class is proper before calling dump.

      <Arguments>
        None

      <Exceptions>
        FormatError: If any of the members of this class are not properly
                     populated.

      <Side Effects>
        None

      <Returns>
        None
    """
    for method in inspect.getmembers(self, predicate=inspect.ismethod):
        if method[0].startswith("_validate_"):
          method[1]()

@attr.s(repr=False, init=False)
class Signable(Metablock):
  """Objects with base class Signable can sign their payload (a canonical
  pretty printed JSON string not containing the signatures attribute) and store
  the signature (signature format: securesystemslib.formats.SIGNATURE_SCHEMA) """
  signatures = attr.ib()

  def __init__(self, **kwargs):
    super(Signable, self).__init__()
    self.signatures =  kwargs.get("signatures", [])

  @property
  def payload(self):
    payload = attr.asdict(self)
    payload.pop("signatures")
    return canonicaljson.encode_pretty_printed_json(payload)

  def sign(self, key):
    """Signs the canonical JSON representation of itself (without the
    signatures property) and adds the signatures to its signature properties."""

    securesystemslib.formats.KEY_SCHEMA.check_match(key)

    signature = securesystemslib.keys.create_signature(key, self.payload)
    self.signatures.append(signature)

  def verify_signatures(self, keys_dict):
    """Verifies all signatures of the object using the passed key_dict."""

    securesystemslib.formats.KEYDICT_SCHEMA.check_match(keys_dict)

    if not self.signatures or len(self.signatures) <= 0:
      raise SignatureVerificationError("No signatures found")

    for signature in self.signatures:
      keyid = signature["keyid"]
      try:
        key = keys_dict[keyid]
      except KeyError:
        raise SignatureVerificationError(
            "Signature key not found, key id is '{0}'".format(keyid))
      if not securesystemslib.keys.verify_signature(
          key, signature, self.payload):
        raise SignatureVerificationError("Invalid signature")

