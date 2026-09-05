// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @notice Records completed games authorized by the Flask server.
/// @dev Correctness is player feedback, not proof of competitive skill.
contract GameScoreboard {
    address public immutable authority;
    mapping(bytes32 => bool) public recorded;
    struct Score { uint256 games; uint256 correctGuesses; uint256 totalQuestions; }
    mapping(address => Score) public scores;
    event ResultRecorded(address indexed player, bytes32 indexed gameId, bool correct, uint256 questions);

    constructor(address signer) {
        require(signer != address(0), "Invalid authority");
        authority = signer;
    }

    function recordResult(bytes32 gameId, bool correct, uint256 questions, uint256 deadline,
                          uint8 v, bytes32 r, bytes32 s) external {
        require(!recorded[gameId], "Already recorded");
        require(block.timestamp <= deadline, "Expired");
        require(questions > 0 && questions <= 1000, "Invalid questions");
        bytes32 payload = keccak256(abi.encode(block.chainid, address(this), msg.sender,
                                                gameId, correct, questions, deadline));
        bytes32 digest = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", payload));
        require(v == 27 || v == 28, "Invalid v");
        require(uint256(s) <= 0x7fffffffffffffffffffffffffffffff5d576e7357a4501ddfe92f46681b20a0, "Invalid s");
        require(ecrecover(digest, v, r, s) == authority, "Invalid signature");
        recorded[gameId] = true;
        Score storage score = scores[msg.sender];
        score.games++;
        if (correct) score.correctGuesses++;
        score.totalQuestions += questions;
        emit ResultRecorded(msg.sender, gameId, correct, questions);
    }
}
